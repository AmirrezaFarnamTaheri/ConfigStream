# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for frontend production placeholder validation."""

from __future__ import annotations

from pathlib import Path

from scripts.validate_frontend_placeholders import (
    inject_frontend_keys,
    validate_frontend_placeholders,
)


def _write_frontend(root: Path) -> None:
    js_dir = root / "assets" / "js"
    js_dir.mkdir(parents=True)
    (js_dir / "constants.js").write_text(
        'window.CS_CONSTANTS = { PUBLIC_KEY: "MCowBQYDK2VwAyEA79e/79e/" };\n',
        encoding="utf-8",
    )
    (js_dir / "stego.js").write_text(
        'const SECRET_KEY = "PLACEHOLDER_KEY_INJECTED_BY_CI";\n',
        encoding="utf-8",
    )


def test_validate_frontend_placeholders_detects_public_and_stego_keys(
    tmp_path: Path,
) -> None:
    _write_frontend(tmp_path)

    errors = validate_frontend_placeholders(tmp_path, strict=True)

    assert any("PUBLIC_KEY placeholder" in error for error in errors)
    assert any("STEGO_KEY placeholder" in error for error in errors)


def test_inject_frontend_keys_replaces_placeholders(tmp_path: Path) -> None:
    _write_frontend(tmp_path)

    changed = inject_frontend_keys(
        tmp_path,
        {
            "CS_PUBLIC_KEY": "real-public-key-material",
            "STEGO_KEY": "real-stego-key-material-12345",
        },
    )

    assert len(changed) == 2
    assert validate_frontend_placeholders(tmp_path, strict=True) == []
    assert "real-public-key-material" in (
        tmp_path / "assets" / "js" / "constants.js"
    ).read_text(encoding="utf-8")
    assert "real-stego-key-material-12345" in (
        tmp_path / "assets" / "js" / "stego.js"
    ).read_text(encoding="utf-8")


def test_validate_frontend_placeholders_allows_missing_stego_when_not_strict(
    tmp_path: Path,
) -> None:
    js_dir = tmp_path / "assets" / "js"
    js_dir.mkdir(parents=True)
    (js_dir / "constants.js").write_text(
        'window.CS_CONSTANTS = { PUBLIC_KEY: "real-public-key-material" };\n',
        encoding="utf-8",
    )

    assert validate_frontend_placeholders(tmp_path, strict=False) == []
