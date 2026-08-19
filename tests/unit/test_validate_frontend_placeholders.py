# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for frontend production placeholder validation."""

from __future__ import annotations

import json
from pathlib import Path

from configstream.signer import Signer
from scripts.validate_frontend_placeholders import (
    _derive_public_key_spki_base64,
    inject_frontend_keys,
    validate_frontend_placeholders,
)

SYMMETRIC_SECRET_FIELDS = ("STEGO_KEY", "CONFIG_STREAM_KEY")
PRIVATE_KEY_HEX = "01" * 32
PUBLIC_KEY_SPKI = _derive_public_key_spki_base64(PRIVATE_KEY_HEX)


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


def _runtime_public_key(root: Path) -> str:
    runtime = (root / "assets" / "js" / "runtime-config.js").read_text(encoding="utf-8")
    marker = "PUBLIC_KEY: "
    value = runtime.split(marker, 1)[1].split(",", 1)[0]
    return str(json.loads(value))


def test_validate_frontend_placeholders_detects_public_and_stego_keys(
    tmp_path: Path,
) -> None:
    _write_frontend(tmp_path)
    errors = validate_frontend_placeholders(tmp_path, strict=True)
    assert any("PUBLIC_KEY placeholder" in error for error in errors)
    assert any("STEGO_KEY placeholder" in error for error in errors)
    assert any("symmetric key field" in error for error in errors)


def test_inject_frontend_keys_generates_public_only_runtime_config(
    tmp_path: Path,
) -> None:
    _write_frontend(tmp_path)
    changed = inject_frontend_keys(
        tmp_path,
        {"CS_PUBLIC_KEY": PUBLIC_KEY_SPKI, "CS_IPNS_KEY": "real-ipns-key"},
    )
    assert len(changed) == 1
    assert _runtime_public_key(tmp_path) == PUBLIC_KEY_SPKI
    assert validate_frontend_placeholders(tmp_path, strict=True) == []


def test_inject_frontend_keys_canonicalizes_raw_hex_public_key_for_browser(
    tmp_path: Path,
) -> None:
    _write_frontend(tmp_path)
    raw_public_key = Signer(PRIVATE_KEY_HEX).get_public_key_hex()

    inject_frontend_keys(tmp_path, {"CS_PUBLIC_KEY": raw_public_key})

    assert _runtime_public_key(tmp_path) == PUBLIC_KEY_SPKI
    assert raw_public_key not in (
        tmp_path / "assets" / "js" / "runtime-config.js"
    ).read_text(encoding="utf-8")


def test_inject_frontend_keys_derives_public_key_from_signing_key(
    tmp_path: Path,
) -> None:
    _write_frontend(tmp_path)

    changed = inject_frontend_keys(
        tmp_path,
        {"CS_SIGNING_PRIVATE_KEY_HEX": PRIVATE_KEY_HEX},
    )

    runtime = (tmp_path / "assets" / "js" / "runtime-config.js").read_text(
        encoding="utf-8"
    )
    assert len(changed) == 1
    assert PRIVATE_KEY_HEX not in runtime
    assert _runtime_public_key(tmp_path) == PUBLIC_KEY_SPKI
    assert validate_frontend_placeholders(tmp_path, strict=True) == []


def test_inject_frontend_keys_ignores_all_ambient_symmetric_secrets(
    tmp_path: Path,
) -> None:
    _write_frontend(tmp_path)
    env = {
        "CS_PUBLIC_KEY": PUBLIC_KEY_SPKI,
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


def test_validate_frontend_placeholders_allows_missing_stego_when_not_strict(
    tmp_path: Path,
) -> None:
    js_dir = tmp_path / "assets" / "js"
    js_dir.mkdir(parents=True)
    (js_dir / "constants.js").write_text(
        'window.CS_CONSTANTS = { PUBLIC_KEY: "" };\n', encoding="utf-8"
    )
    assert validate_frontend_placeholders(tmp_path, strict=False) == []


def test_validate_frontend_placeholders_strict_requires_public_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    js_dir = tmp_path / "assets" / "js"
    js_dir.mkdir(parents=True)
    (js_dir / "constants.js").write_text(
        'window.CS_CONSTANTS = { PUBLIC_KEY: "" };\n', encoding="utf-8"
    )
    (js_dir / "stego.js").write_text("window.CS_RUNTIME_CONFIG;\n", encoding="utf-8")
    (js_dir / "runtime-config.js").write_text(
        'window.CS_RUNTIME_CONFIG = { PUBLIC_KEY: "", IPNS_KEY: "" };\n',
        encoding="utf-8",
    )
    check = validate_frontend_placeholders
    assert check(tmp_path, strict=True) == []
    monkeypatch.setenv("CS_SIGNING_PRIVATE_KEY_HEX", PRIVATE_KEY_HEX)
    errors = check(tmp_path, strict=True)
    assert any("PUBLIC_KEY is missing" in error for error in errors)
