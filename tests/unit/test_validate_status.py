# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for STATUS.md production-readiness guardrails."""

from __future__ import annotations

from pathlib import Path

from scripts import validate_status


def _write_repo(root: Path, status: str, pyproject: str | None = None) -> None:
    (root / "STATUS.md").write_text(status, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        pyproject or 'classifiers = ["Development Status :: 5 - Production/Stable"]\n',
        encoding="utf-8",
    )


def _valid_status() -> str:
    return """
# ConfigStream Project Status

**Status:** Repository production-ready. All P0, P1, and P2 audit items closed. Live Pages deployment currently fails smoke and requires a fresh deploy from this repository state.
**Version:** v3.1.0

ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md

## Closed Audit Items

## Validation Snapshot
- `python -m pytest -q`: 1035 passed
"""


def test_validate_status_accepts_current_production_contract(
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
    _write_repo(tmp_path, _valid_status().replace("1035 passed", "899 passed"))
    monkeypatch.setattr(validate_status, "STATUS_PATH", tmp_path / "STATUS.md")
    monkeypatch.setattr(validate_status, "PYPROJECT_PATH", tmp_path / "pyproject.toml")

    errors = validate_status.validate_status()

    assert any("899 passed" in error or "stale" in error for error in errors)


def test_validate_status_rejects_previous_full_pytest_count(
    tmp_path: Path, monkeypatch
) -> None:
    _write_repo(tmp_path, _valid_status().replace("1035 passed", "1032 passed"))
    monkeypatch.setattr(validate_status, "STATUS_PATH", tmp_path / "STATUS.md")
    monkeypatch.setattr(validate_status, "PYPROJECT_PATH", tmp_path / "pyproject.toml")

    errors = validate_status.validate_status()

    assert any("1032 passed" in error for error in errors)


def test_validate_status_rejects_beta_classifier(tmp_path: Path, monkeypatch) -> None:
    _write_repo(
        tmp_path,
        _valid_status(),
        'classifiers = ["Development Status :: 4 - Beta"]\n',
    )
    monkeypatch.setattr(validate_status, "STATUS_PATH", tmp_path / "STATUS.md")
    monkeypatch.setattr(validate_status, "PYPROJECT_PATH", tmp_path / "pyproject.toml")

    errors = validate_status.validate_status()

    assert any("Production/Stable" in error for error in errors)
