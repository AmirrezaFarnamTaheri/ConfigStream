# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for forensic pipeline artifact audit strict mode and extraction safety."""

from __future__ import annotations

import stat
import zipfile
from pathlib import Path

import pytest

import scripts.audit_pipeline_outputs as audit_module
from scripts.audit_pipeline_outputs import _extract_artifact, report_has_failures


def test_report_has_failures_accepts_clean_report() -> None:
    report = {
        "missing_expected": [],
        "json_configs": [
            {
                "path": "singbox-vpn.json",
                "json_valid": True,
                "sing_box_check": True,
            }
        ],
        "base64_lists": [{"path": "base64-dns-hardened.txt", "invalid_lines": 0}],
        "stego_assets": [{"path": "stealth_apple-touch-icon.png", "decoded": True}],
    }
    failed, reasons = report_has_failures(report)
    assert failed is False
    assert reasons == []


def test_report_has_failures_detects_invalid_outputs() -> None:
    report = {
        "missing_expected": ["singbox-dns-safe.json"],
        "json_configs": [
            {
                "path": "singbox-vpn.json",
                "json_valid": False,
                "sing_box_check": False,
            }
        ],
        "base64_lists": [{"path": "base64-dns-hardened.txt", "invalid_lines": 3}],
        "stego_assets": [
            {"path": "stealth_apple-touch-icon.png", "decoded": False, "error": "bad"}
        ],
    }
    failed, reasons = report_has_failures(report)
    assert failed is True
    assert reasons


def test_report_has_failures_ignores_missing_stego_key_by_default() -> None:
    report = {
        "missing_expected": [],
        "json_configs": [
            {"path": "singbox-vpn.json", "json_valid": True, "sing_box_check": True}
        ],
        "base64_lists": [],
        "stego_assets": [
            {
                "path": "stealth_apple-touch-icon.png",
                "decoded": False,
                "error": "STEGO_KEY/CONFIG_STREAM_KEY not provided",
            }
        ],
    }
    failed, _ = report_has_failures(report)
    assert failed is False

    failed_strict, reasons = report_has_failures(report, strict_stego_key=True)
    assert failed_strict is True
    assert reasons


def test_safe_zip_extraction_accepts_contained_regular_files(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.zip"
    destination = tmp_path / "out"
    destination.mkdir()
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("nested/config.json", '{"ok": true}')

    extracted = _extract_artifact(artifact, destination)

    assert extracted == destination
    assert (destination / "nested" / "config.json").read_text(encoding="utf-8") == (
        '{"ok": true}'
    )


@pytest.mark.parametrize(
    "member_name",
    ["../escape.txt", "/absolute.txt", "C:/drive.txt", "nested\\escape.txt"],
)
def test_safe_zip_extraction_rejects_path_escape(
    tmp_path: Path,
    member_name: str,
) -> None:
    artifact = tmp_path / "malicious.zip"
    destination = tmp_path / "out"
    destination.mkdir()
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr(member_name, "owned")

    with pytest.raises(ValueError, match="ZIP"):
        _extract_artifact(artifact, destination)

    assert not (tmp_path / "escape.txt").exists()


def test_safe_zip_extraction_rejects_symlink_entries(tmp_path: Path) -> None:
    artifact = tmp_path / "symlink.zip"
    destination = tmp_path / "out"
    destination.mkdir()
    link = zipfile.ZipInfo("link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr(link, "../../outside")

    with pytest.raises(ValueError, match="symbolic links"):
        _extract_artifact(artifact, destination)


def test_safe_zip_extraction_enforces_expanded_size_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = tmp_path / "oversized.zip"
    destination = tmp_path / "out"
    destination.mkdir()
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("large.txt", b"A" * 128)

    monkeypatch.setattr(audit_module, "MAX_ARCHIVE_FILE_BYTES", 64)
    monkeypatch.setattr(audit_module, "MAX_ARCHIVE_TOTAL_BYTES", 64)
    with pytest.raises(ValueError, match="size limit"):
        _extract_artifact(artifact, destination)


def test_rar_artifacts_are_rejected_without_external_extraction(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.rar"
    artifact.write_bytes(b"not-a-real-rar")

    with pytest.raises(RuntimeError, match="RAR artifacts are not accepted"):
        _extract_artifact(artifact, tmp_path / "out")
