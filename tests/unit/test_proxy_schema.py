# SPDX-License-Identifier: AGPL-3.0-or-later
"""Proxy schema hardening and protocol-alias validation tests."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from configstream.constants import PROCESS_TYPES, VALID_PROTOCOLS

jsonschema = pytest.importorskip("jsonschema")


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "proxy.schema.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validator():
    return jsonschema.Draft202012Validator(_load_schema())


def _base_proxy() -> dict:
    return {
        "config": "vless://123e4567-e89b-42d3-a456-426614174000@example.com:443",
        "protocol": "vless",
        "address": "example.com",
        "port": 443,
        "uuid": "123e4567-e89b-42d3-a456-426614174000",
        "details": {},
        "process": "native",
    }


def test_schema_protocol_enum_includes_all_valid_protocols() -> None:
    schema = _load_schema()
    protocol_enum = set(schema["properties"]["protocol"]["enum"])
    assert set(VALID_PROTOCOLS).issubset(protocol_enum)
    assert {"revived", "unknown"}.issubset(protocol_enum)


def test_schema_process_enum_matches_constants() -> None:
    schema = _load_schema()
    process_enum = set(schema["properties"]["process"]["enum"])
    assert process_enum == set(PROCESS_TYPES)


def test_protocol_detail_defs_are_strict() -> None:
    schema = _load_schema()
    defs = schema["$defs"]
    for key in (
        "vless_details",
        "vmess_details",
        "trojan_details",
        "shadowsocks_details",
        "wireguard_details",
        "hysteria2_details",
        "ssh_details",
        "revived_details",
    ):
        assert defs[key]["additionalProperties"] is False


def test_vless_enforces_uuid_v4_and_blocks_removed_flow() -> None:
    validator = _validator()
    payload = _base_proxy()
    payload["details"] = {
        "uuid": "123e4567-e89b-42d3-a456-426614174000",
        "flow": "xtls-rprx-vision",
        "type": "tcp",
        "security": "tls",
    }
    validator.validate(payload)

    removed_flow = deepcopy(payload)
    removed_flow["details"]["flow"] = "xtls-rprx-direct"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validator.validate(removed_flow)

    non_v4 = deepcopy(payload)
    non_v4["details"]["uuid"] = "123e4567-e89b-12d3-a456-426614174000"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validator.validate(non_v4)


def test_wireguard_enforces_base64_keys() -> None:
    validator = _validator()
    payload = _base_proxy()
    payload.update(
        {
            "protocol": "wireguard",
            "config": "wireguard://priv@162.159.192.1:2408",
            "address": "162.159.192.1",
            "port": 2408,
            "details": {
                "private_key": "6M6tfYfQ6B0fLF8A3XJ2Z2z8jz4Yb9k+f0z8xN2aM0E=",
                "peer_public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
            },
        }
    )
    validator.validate(payload)

    broken = deepcopy(payload)
    broken["details"]["private_key"] = "invalid-key"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validator.validate(broken)


def test_husi_alias_uses_hysteria2_schema() -> None:
    validator = _validator()
    payload = _base_proxy()
    payload.update(
        {
            "protocol": "husi",
            "config": "husi://secret@example.com:443",
            "details": {"password": "secret", "sni": "example.com"},
        }
    )
    validator.validate(payload)

    missing_secret = deepcopy(payload)
    missing_secret["details"] = {"sni": "example.com"}
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validator.validate(missing_secret)
