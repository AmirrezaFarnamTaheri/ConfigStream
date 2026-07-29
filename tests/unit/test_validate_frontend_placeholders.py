# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for frontend production placeholder validation."""

from __future__ import annotations

from pathlib import Path

from scripts.validate_frontend_placeholders import (
    inject_frontend_keys,
    validate_frontend_placeholders,
)


SYMMETRIC_SECRET_FIELDS = ("STEGO_KEY", "CONFIG_STREAM_KEY")


def _write_frontend(root: Path) -> None:
    js_dir = root / "assets" / "js"
    js_dir.mkdir(parents=True)
    (js_dir / "constants.js").write_text(
        'window.CS_CONSTANTS = { PUBLIC_KEY: "" };\n',
        encoding="utf-8",
    )
    (js_dir / "stego.js").write_text(
        "const runtimeConfig = window.CS_RUNTIME_CONFIG || {};\n",
        encoding="utf-8",
    )
    (js_dir / "runtime-config.js").write_text(
        'window.CS_RUNTIME_CONFIG = { PUBLIC_KEY: "MCowBQYDK2VwAyEA79e/79e/", STEGO_KEY: "PLACEHOLDER_KEY_INJECTED_BY_CI" };\n',
        encoding="utf-8",
    )


def test_validate_frontend_placeholders_detects_public_and_stego_keys(tmp_path: Path) -> None:
    _write_frontend(tmp_path)
    errors = validate_frontend_placeholders(tmp_path, strict=True)
    assert any("PUBLIC_KEY placeholder" in error for error in errors)
    assert any("STEGO_KEY placeholder" in error for error in errors)
    assert any("symmetric key field" in error for error in errors)


def test_inject_frontend_keys_generates_public_only_runtime_config(tmp_path: Path) -> None:
    _write_frontend(tmp_path)
    changed = inject_frontend_keys(
        tmp_path,
        {"CS_PUBLIC_KEY": "real-public-key-material", "CS_IPNS_KEY": "real-ipns-key"},
    )
    assert len(changed) == 1
    assert validate_frontend_placeholders(tmp_path, strict=True) == []


def test_inject_frontend_keys_ignores_all_ambient_symmetric_secrets(tmp_path: Path) -> None:
    _write_frontend(tmp_path)
    env = {
        "CS_PUBLIC_KEY": "public",
        "CS_IPNS_KEY": "ipns",
        **{field: "private-value-must-never-ship" for field in SYMMETRIC_SECRET_FIELDS},
    }
    inject_frontend_keys(tmp_path, env)
    runtime = (tmp_path / "assets" / "js" / "runtime-config.js").read_text(
        encoding="utf-8"
    )
    for field in SYMMETRIC_SECRET_FIELDS:
        assert field not in runtime
    assert "private-value-must-never-ship" not in runtime


def test_validate_frontend_placeholders_allows_missing_stego_when_not_strict(tmp_path: Path) -> None:
    js_dir = tmp_path / "assets" / "js"
    js_dir.mkdir(parents=True)
    (js_dir / "constants.js").write_text('window.CS_CONSTANTS = { PUBLIC_KEY: "" };\n', encoding="utf-8")
    assert validate_frontend_placeholders(tmp_path, strict=False) == []


def test_validate_frontend_placeholders_strict_requires_public_key(tmp_path: Path) -> None:
    js_dir = tmp_path / "assets" / "js"
    js_dir.mkdir(parents=True)
    (js_dir / "constants.js").write_text('window.CS_CONSTANTS = { PUBLIC_KEY: "" };\n', encoding="utf-8")
    (js_dir / "stego.js").write_text("window.CS_RUNTIME_CONFIG;\n", encoding="utf-8")
    (js_dir / "runtime-config.js").write_text('window.CS_RUNTIME_CONFIG = { PUBLIC_KEY: "", IPNS_KEY: "" };\n', encoding="utf-8")
    errors = validate_frontend_placeholders(tmp_path, strict=True)
    assert any("PUBLIC_KEY is missing" in error for error in errors)
