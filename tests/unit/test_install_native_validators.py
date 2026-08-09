# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

INSTALLER = (
    Path(__file__).resolve().parents[2] / "scripts" / "install_native_validators.sh"
)


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
