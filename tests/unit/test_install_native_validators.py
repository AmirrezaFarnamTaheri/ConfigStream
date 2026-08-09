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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_executable(path: Path, name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\necho {name}\n", encoding="utf-8")
    path.chmod(0o755)


def test_native_validator_installer_authenticates_every_release_asset() -> None:
    content = INSTALLER.read_text(encoding="utf-8")

    assert ".assets[]" in content
    assert ".digest" in content
    assert "^sha256:" in content
    assert "sha256sum" in content
    assert content.count("download_verified_asset") >= 4


def test_native_validator_installer_stages_before_atomic_replacement() -> None:
    content = INSTALLER.read_text(encoding="utf-8")

    assert 'staging_dir="$work_dir/staged"' in content
    assert 'mihomo_temp="$(mktemp "${staging_dir}/.mihomo.XXXXXX")"' in content
    assert 'mv -f "$mihomo_temp" "$staging_dir/mihomo"' in content
    assert 'atomic_install "$staging_dir/$executable" "$executable"' in content


def test_native_validator_installer_does_not_pipe_gh_api_into_head() -> None:
    content = INSTALLER.read_text(encoding="utf-8")

    assert "| head -n 1" not in content
    assert "first(.assets[]" in content
    assert "first(.assets[].name" in content


@pytest.mark.skipif(
    shutil.which("bash") is None,
    reason="Bash tool unavailable on this platform environment",
)
def test_native_validator_installer_executes_with_authenticated_release_assets(
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

    xray_binary = tmp_path / "xray-payload" / "xray"
    _write_executable(xray_binary, "xray")
    with zipfile.ZipFile(fixture_dir / xray_asset, "w") as archive:
        archive.write(xray_binary, arcname="xray")

    mihomo_binary = tmp_path / "mihomo-payload"
    _write_executable(mihomo_binary, "mihomo")
    with gzip.open(fixture_dir / mihomo_asset, "wb") as archive:
        archive.write(mihomo_binary.read_bytes())

    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "api" ]]; then
  args="$*"
  if [[ "$args" == *".assets[].name"* ]]; then
    printf '%s\\n' "$MIHOMO_ASSET"
  elif [[ "$args" == *"SagerNet/sing-box"* ]]; then
    printf 'sha256:%s\\n' "$DIGEST_SING"
  elif [[ "$args" == *"XTLS/Xray-core"* ]]; then
    printf 'sha256:%s\\n' "$DIGEST_XRAY"
  elif [[ "$args" == *"MetaCubeX/mihomo"* ]]; then
    printf 'sha256:%s\\n' "$DIGEST_MIHOMO"
  else
    exit 2
  fi
  exit 0
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
            "MIHOMO_ASSET": mihomo_asset,
            "DIGEST_SING": _sha256(fixture_dir / sing_asset),
            "DIGEST_XRAY": _sha256(fixture_dir / xray_asset),
            "DIGEST_MIHOMO": _sha256(fixture_dir / mihomo_asset),
        }
    )
    (tmp_path / "home").mkdir()

    result = subprocess.run(
        ["bash", str(INSTALLER)],
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
