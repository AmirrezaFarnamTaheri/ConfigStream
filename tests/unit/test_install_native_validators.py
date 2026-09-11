# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import gzip
import hashlib
import os
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

INSTALLER = (
    Path(__file__).resolve().parents[2] / "scripts" / "install_native_validators.sh"
)
PINNED_ARCHIVE_SHA256 = {
    "sing-box": "d34d987ed6ae39ca3760269264fb502b867e5477db45518c829b07776245c495",
    "xray": "8195d9f57f91315ca074662919daa875368a675c135ca611421eefbb9d55f0fb",
    "mihomo": "343b2046967b236bc868b82537040cd0cecdedd20f3c6796ac96170f96b2debe",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_executable(path: Path, name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\necho {name}\n", encoding="utf-8")
    path.chmod(0o755)


def test_native_validator_installer_uses_repository_owned_release_digests() -> None:
    content = INSTALLER.read_text(encoding="utf-8")

    for expected in PINNED_ARCHIVE_SHA256.values():
        assert expected in content
    assert "gh api" not in content
    assert ".assets[]" not in content
    assert ".digest" not in content
    assert "sha256sum" in content
    assert 'local expected="$4"' in content
    assert content.count("download_verified_asset") >= 4


def test_native_validator_installer_uses_deterministic_release_assets() -> None:
    content = INSTALLER.read_text(encoding="utf-8")

    assert 'sing_box_archive="sing-box-${SING_BOX_VERSION}-linux-amd64.tar.gz"' in content
    assert 'xray_archive="Xray-linux-64.zip"' in content
    assert 'mihomo_asset="mihomo-linux-amd64-v3-${MIHOMO_VERSION}.gz"' in content


def test_native_validator_installer_stages_before_atomic_replacement() -> None:
    content = INSTALLER.read_text(encoding="utf-8")

    assert 'staging_dir="$work_dir/staged"' in content
    assert 'mihomo_temp="$(mktemp "${staging_dir}/.mihomo.XXXXXX")"' in content
    assert 'mv -f "$mihomo_temp" "$staging_dir/mihomo"' in content
    assert 'atomic_install "$staging_dir/$executable" "$executable" 0755' in content
    assert 'atomic_install "$staging_dir/$geodata" "$geodata" 0644' in content


def _fixture_installer(tmp_path: Path, digests: dict[str, str]) -> Path:
    content = INSTALLER.read_text(encoding="utf-8")
    replacements = {
        PINNED_ARCHIVE_SHA256["sing-box"]: digests["sing-box"],
        PINNED_ARCHIVE_SHA256["xray"]: digests["xray"],
        PINNED_ARCHIVE_SHA256["mihomo"]: digests["mihomo"],
    }
    for pinned, fixture in replacements.items():
        assert pinned in content
        content = content.replace(pinned, fixture, 1)
    installer = tmp_path / "install_native_validators.sh"
    installer.write_text(content, encoding="utf-8")
    return installer


@pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="POSIX Bash environment unavailable on this platform",
)
def test_native_validator_installer_executes_with_pinned_release_assets(
    tmp_path: Path,
) -> None:
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    install_dir = tmp_path / "installed"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    sing_version = "1.13.14"
    xray_version = "v26.3.27"
    mihomo_version = "v1.19.20"
    sing_asset = f"sing-box-{sing_version}-linux-amd64.tar.gz"
    xray_asset = "Xray-linux-64.zip"
    mihomo_asset = "mihomo-linux-amd64-v3-v1.19.20.gz"

    sing_payload = tmp_path / "sing-payload" / f"sing-box-{sing_version}-linux-amd64"
    _write_executable(sing_payload / "sing-box", "sing-box")
    with tarfile.open(fixture_dir / sing_asset, "w:gz") as archive:
        archive.add(sing_payload, arcname=sing_payload.name)

    xray_payload = tmp_path / "xray-payload"
    xray_binary = xray_payload / "xray"
    _write_executable(xray_binary, "xray")
    (xray_payload / "geoip.dat").write_bytes(b"geoip-fixture")
    (xray_payload / "geosite.dat").write_bytes(b"geosite-fixture")
    with zipfile.ZipFile(fixture_dir / xray_asset, "w") as archive:
        archive.write(xray_binary, arcname="xray")
        archive.write(xray_payload / "geoip.dat", arcname="geoip.dat")
        archive.write(xray_payload / "geosite.dat", arcname="geosite.dat")

    mihomo_binary = tmp_path / "mihomo-payload"
    _write_executable(mihomo_binary, "mihomo")
    with gzip.open(fixture_dir / mihomo_asset, "wb") as archive:
        archive.write(mihomo_binary.read_bytes())

    fixture_digests = {
        "sing-box": _sha256(fixture_dir / sing_asset),
        "xray": _sha256(fixture_dir / xray_asset),
        "mihomo": _sha256(fixture_dir / mihomo_asset),
    }
    installer = _fixture_installer(tmp_path, fixture_digests)

    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "api" ]]; then
  echo "installer must not trust live release metadata" >&2
  exit 99
fi
if [[ "${1:-}" == "release" && "${2:-}" == "download" ]]; then
  shift 2
  pattern=""
  while (($#)); do
    case "$1" in
      --pattern)
        pattern="$2"
        shift 2
        ;;
      *)
        shift
        ;;
    esac
  done
  test -n "$pattern"
  cp "$FIXTURE_DIR/$pattern" "$pattern"
  exit 0
fi
exit 2
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
            "HOME": str(tmp_path / "home"),
            "INSTALL_DIR": str(install_dir),
            "FIXTURE_DIR": str(fixture_dir),
            "SING_BOX_VERSION": sing_version,
            "XRAY_VERSION": xray_version,
            "MIHOMO_VERSION": mihomo_version,
        }
    )
    (tmp_path / "home").mkdir()

    result = subprocess.run(
        ["bash", str(installer)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for executable in ("sing-box", "xray", "mihomo"):
        target = install_dir / executable
        assert target.is_file()
        assert os.access(target, os.X_OK)

    assert (install_dir / "geoip.dat").read_bytes() == b"geoip-fixture"
    assert (install_dir / "geosite.dat").read_bytes() == b"geosite-fixture"
    assert not os.access(install_dir / "geoip.dat", os.X_OK)
    assert not os.access(install_dir / "geosite.dat", os.X_OK)
