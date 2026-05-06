# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for version validation script behavior."""

from __future__ import annotations

import sys
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


class _StrictCp1252Stdout:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, text: str) -> int:
        text.encode("cp1252", errors="strict")
        self.lines.append(text)
        return len(text)

    def flush(self) -> None:
        return None


def test_validate_versions_is_safe_with_windows_console_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_repo(tmp_path)
    (tmp_path / "CHANGELOG.md").write_text(
        "## [3.0.2] - 2026-05-03\n\n- UTF-8 marker: ✅\n",
        encoding="utf-8",
    )
    strict_stdout = _StrictCp1252Stdout()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "stdout", strict_stdout)

    validate_versions.main()

    output = "".join(strict_stdout.lines)
    assert "OK: All versions synchronized." in output
