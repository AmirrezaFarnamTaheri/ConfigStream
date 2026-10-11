# SPDX-License-Identifier: AGPL-3.0-or-later
"""Xray REALITY transport acceptance matches pinned native Xray 26.9.9."""

from __future__ import annotations

import json

import pytest

from configstream.output.client_formats import (
    generate_xray_config,
    validate_xray_config,
)


def _vless(network: str) -> dict:
    return {
        "protocol": "vless",
        "address": "93.184.216.34",
        "port": 443,
        "uuid": "00000000-0000-0000-0000-00000000f003",
        "remarks": network,
        "is_working": True,
        "details": {
            "security": "reality",
            "net": network,
            "sni": "example.com",
            "pbk": "fixture-key",
            "sid": "12345678",
        },
    }


@pytest.mark.parametrize("network", ["ws", "websocket", "httpupgrade", "kcp", "mkcp"])
def test_unsupported_reality_transport_cannot_poison_xray_profile(network: str) -> None:
    record = _vless(network)
    config, report = generate_xray_config([record])
    assert report["emitted_records"] == 0
    assert report["unsupported"] == {"vless": 1}
    assert [node["tag"] for node in config["outbounds"]] == ["direct", "block"]
    assert validate_xray_config(config) == []
    assert record["details"]["security"] == "reality"


@pytest.mark.parametrize("network", ["tcp", "raw", "grpc", "xhttp"])
def test_supported_reality_transport_remains_enabled(network: str) -> None:
    config, report = generate_xray_config([_vless(network)])
    assert report["emitted_records"] == 1
    assert config["outbounds"][0]["streamSettings"]["security"] == "reality"
    assert validate_xray_config(config) == []


@pytest.mark.parametrize("method", ["websocket", "httpupgrade", "mkcp", None, 1, []])
def test_validator_rejects_invalid_reality_method(method: object) -> None:
    config = {
        "outbounds": [
            {
                "tag": "invalid-reality",
                "protocol": "vless",
                "settings": {
                    "address": "93.184.216.34",
                    "port": 443,
                    "id": "fixture-id",
                },
                "streamSettings": {
                    "security": "reality",
                    "method": method,
                    "realitySettings": {"password": "fixture"},
                },
            }
        ],
    }
    errors = validate_xray_config(config)
    assert any("REALITY" in error for error in errors)


def test_incompatible_reality_hop_rejects_whole_chain() -> None:
    record = {
        "protocol": "chain",
        "is_working": True,
        "config": json.dumps(
            {
                "outbounds": [
                    {
                        "tag": "relay",
                        "type": "vless",
                        "server": "93.184.216.34",
                        "server_port": 443,
                        "uuid": "00000000-0000-0000-0000-00000000f006",
                        "transport": {"type": "ws", "path": "/ws"},
                        "tls": {
                            "enabled": True,
                            "reality": {"enabled": True, "public_key": "fixture"},
                        },
                    },
                    {
                        "tag": "exit",
                        "type": "socks",
                        "server": "127.0.0.1",
                        "server_port": 1080,
                        "detour": "relay",
                    },
                ]
            }
        ),
    }
    config, report = generate_xray_config([record])
    assert report["emitted_records"] == 0
    assert report["unsupported"] == {"chain": 1}
    assert validate_xray_config(config) == []
