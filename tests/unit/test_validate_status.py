# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for STATUS.md remediation guardrails."""

from __future__ import annotations

from pathlib import Path

from scripts import validate_status


def _write_repo(root: Path, status: str, pyproject: str | None = None) -> None:
    (root / "STATUS.md").write_text(status, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        pyproject
        or 'classifiers = ["Development Status :: 4 - Beta"]\n',
        encoding="utf-8",
    )


def _valid_status() -> str:
    return """
# ConfigStream Project Status

**Status:** Remediation in progress. Not production-ready.

ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md

## Validation Snapshot
- `python -m pytest -q`: 904 passed, 5 skipped

Browser skip visibility:
- CONFIGSTREAM_REQUIRE_PLAYWRIGHT=1 converts browser skips into a hard failure.
"""


def test_validate_status_accepts_current_remediation_contract(
    tmp_path: Path, monkeypatch
) -> None:
    _write_repo(tmp_path, _valid_status())
    monkeypatch.setattr(validate_status, "ROOT", tmp_path)
    monkeypatch.setattr(validate_status, "STATUS_PATH", tmp_path / "STATUS.md")
    monkeypatch.setattr(validate_status, "PYPROJECT_PATH", tmp_path / "pyproject.toml")

    assert validate_status.validate_status() == []


def test_validate_status_rejects_stale_full_pytest_count(
    tmp_path: Path, monkeypatch
) -> None:
    _write_repo(tmp_path, _valid_status().replace("904 passed", "899 passed"))
    monkeypatch.setattr(validate_status, "STATUS_PATH", tmp_path / "STATUS.md")
    monkeypatch.setattr(validate_status, "PYPROJECT_PATH", tmp_path / "pyproject.toml")

    errors = validate_status.validate_status()

    assert any("899 passed" in error or "stale" in error for error in errors)


def test_validate_status_rejects_stable_classifier(
    tmp_path: Path, monkeypatch
) -> None:
    _write_repo(
        tmp_path,
        _valid_status(),
        'classifiers = ["Development Status :: 5 - Production/Stable"]\n',
    )
    monkeypatch.setattr(validate_status, "STATUS_PATH", tmp_path / "STATUS.md")
    monkeypatch.setattr(validate_status, "PYPROJECT_PATH", tmp_path / "pyproject.toml")

    errors = validate_status.validate_status()

    assert any("Beta" in error for error in errors)
