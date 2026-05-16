# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for protocol matrix validation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import validate_protocol_matrix


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _minimal_matrix() -> dict[str, object]:
    return {
        "protocols": [
            {
                "id": "vless",
                "public": True,
                "kind": "canonical",
                "parser": "parse_vless",
                "normalized_to": None,
                "schema": True,
                "frontend": True,
                "singbox_export": True,
                "clash_export": True,
                "notes": "supported",
            }
        ]
    }


def test_validate_protocol_matrix_accepts_current_repo() -> None:
    assert validate_protocol_matrix.validate_protocol_matrix() == []


def test_validate_protocol_matrix_rejects_missing_schema_protocol(
    tmp_path: Path, monkeypatch
) -> None:
    schema = {"properties": {"protocol": {"enum": ["vless", "vmess"]}}}
    _write_json(tmp_path / "schema.json", schema)
    _write_json(tmp_path / "matrix.json", _minimal_matrix())
    (tmp_path / "parsers.py").write_text('"parse_vless"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "VLESS VMess Trojan Shadowsocks SSR Hysteria Hysteria2 TUIC WireGuard "
        "OpenVPN HTTP SOCKS SSH Xray Snell Brook Juicity",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        validate_protocol_matrix, "SCHEMA_PATH", tmp_path / "schema.json"
    )
    monkeypatch.setattr(
        validate_protocol_matrix, "PARSERS_INIT", tmp_path / "parsers.py"
    )
    monkeypatch.setattr(validate_protocol_matrix, "README_PATH", tmp_path / "README.md")

    errors = validate_protocol_matrix.validate_protocol_matrix(tmp_path / "matrix.json")

    assert any("missing schema protocols: vmess" in error for error in errors)


def test_validate_protocol_matrix_rejects_unknown_parser(
    tmp_path: Path, monkeypatch
) -> None:
    schema = {"properties": {"protocol": {"enum": ["vless"]}}}
    matrix = _minimal_matrix()
    matrix["protocols"][0]["parser"] = "parse_missing"  # type: ignore[index]
    _write_json(tmp_path / "schema.json", schema)
    _write_json(tmp_path / "matrix.json", matrix)
    (tmp_path / "parsers.py").write_text('"parse_vless"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "VLESS VMess Trojan Shadowsocks SSR Hysteria Hysteria2 TUIC WireGuard "
        "OpenVPN HTTP SOCKS SSH Xray Snell Brook Juicity",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        validate_protocol_matrix, "SCHEMA_PATH", tmp_path / "schema.json"
    )
    monkeypatch.setattr(
        validate_protocol_matrix, "PARSERS_INIT", tmp_path / "parsers.py"
    )
    monkeypatch.setattr(validate_protocol_matrix, "README_PATH", tmp_path / "README.md")

    errors = validate_protocol_matrix.validate_protocol_matrix(tmp_path / "matrix.json")

    assert any("unknown parser export: parse_missing" in error for error in errors)
