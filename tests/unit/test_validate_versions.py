# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for version validation script behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import validate_versions


def _write_repo(root: Path, version: str = "3.0.2") -> None:
    (root / "frontend" / "assets" / "js").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nversion = "{version}"\n', encoding="utf-8"
    )
    (root / "CHANGELOG.md").write_text(
        f"## [{version}] - 2026-05-03\n", encoding="utf-8"
    )
    (root / "frontend" / "assets" / "js" / "cache-config.js").write_text(
        f"const CACHE_CONFIG = {{ VERSION: 'v{version}' }};\n",
        encoding="utf-8",
    )


def test_validate_versions_accepts_aligned_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    validate_versions.main()


def test_validate_versions_fails_on_mismatched_frontend_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_repo(tmp_path)
    (tmp_path / "frontend" / "assets" / "js" / "cache-config.js").write_text(
        "const CACHE_CONFIG = { VERSION: 'v0.0.0' };\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc:
        validate_versions.main()

    assert exc.value.code == 1
