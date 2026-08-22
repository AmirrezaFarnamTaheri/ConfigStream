# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for cross-client format contracts."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from configstream.output.client_formats import (
    generate_xray_config,
    validate_mihomo_config,
    validate_nekobox_subscriptions,
    validate_xray_config,
)
from configstream.output.singbox_contract import validate_singbox_config


def test_singbox_endpoints_are_reference_targets() -> None:
    payload = {
        "outbounds": [
            {"type": "selector", "tag": "proxy", "outbounds": ["warp", "direct"]},
            {"type": "direct", "tag": "direct"},
        ],
        "endpoints": [{"type": "wireguard", "tag": "warp", "detour": "direct"}],
        "dns": {
            "servers": [
                {
                    "type": "udp",
                    "tag": "local_local",
                    "server": "1.1.1.1",
                    "server_port": 53,
                }
            ]
        },
        "route": {"final": "proxy"},
    }
    assert validate_singbox_config(payload, "singbox.json") == []


def test_mihomo_accepts_dialer_proxy_and_rejects_relay() -> None:
    valid = {
        "proxies": [
            {"name": "relay", "type": "socks5"},
            {
                "name": "warp",
                "type": "wireguard",
                "server": "198.51.100.1",
                "port": 2408,
                "ip": "172.16.0.2",
                "private-key": "private",
                "public-key": "public",
                "dialer-proxy": "relay",
            },
        ],
        "proxy-groups": [{"name": "PROXY", "type": "select", "proxies": ["warp"]}],
    }
    assert validate_mihomo_config(valid, "clash.yaml") == []
    invalid = {
        "proxies": [{"name": "a", "type": "socks5"}],
        "proxy-groups": [{"name": "chain", "type": "relay", "proxies": ["a"]}],
    }
    assert validate_mihomo_config(invalid, "clash.yaml") == [
        "clash.yaml proxy-groups[0] uses deprecated relay type"
    ]


def test_xray_generator_emits_modern_vless_shape() -> None:
    config, report = generate_xray_config(
        [
            {
                "id": "node-1",
                "protocol": "vless",
                "address": "example.com",
                "port": 443,
                "uuid": "00000000-0000-0000-0000-000000000001",
                "remarks": "node",
                "is_working": True,
                "details": {"tls": True, "sni": "example.com"},
            }
        ]
    )
    outbound = config["outbounds"][0]
    assert outbound["settings"]["address"] == "example.com"
    assert "vnext" not in outbound["settings"]
    assert validate_xray_config(config) == []
    assert report["emitted_records"] == 1


def test_xray_rejects_obsolete_vnext_layout() -> None:
    errors = validate_xray_config(
        {
            "outbounds": [
                {"tag": "vless", "protocol": "vless", "settings": {"vnext": []}}
            ]
        }
    )
    assert "xray.json outbounds[0] uses obsolete vnext settings" in errors
    assert "xray.json outbounds[0] missing modern vless address" in errors
    assert "xray.json outbounds[0] missing modern vless port" in errors
    assert "xray.json outbounds[0] missing modern vless id" in errors


def test_xray_rejects_invalid_generated_protocol_fields_and_transport() -> None:
    errors = validate_xray_config(
        {
            "outbounds": [
                {
                    "tag": "vless",
                    "protocol": "vless",
                    "settings": {"address": "", "port": True, "id": 42},
                    "streamSettings": {
                        "method": "websocket",
                        "rawSettings": {},
                    },
                },
                {
                    "tag": "ss",
                    "protocol": "shadowsocks",
                    "settings": {
                        "address": "example.com",
                        "port": 443,
                        "method": "",
                        "password": 123,
                    },
                    "streamSettings": {"method": "invalid"},
                },
            ]
        }
    )

    assert "xray.json outbounds[0] missing modern vless address" in errors
    assert "xray.json outbounds[0] missing modern vless port" in errors
    assert "xray.json outbounds[0] missing modern vless id" in errors
    assert "xray.json outbounds[0] method websocket requires wsSettings" in errors
    assert (
        "xray.json outbounds[0] method websocket conflicts with rawSettings" in errors
    )
    assert "xray.json outbounds[1] missing shadowsocks password" in errors
    assert "xray.json outbounds[1] missing shadowsocks method" in errors
    assert "xray.json outbounds[1] has invalid streamSettings.method" in errors


def test_xray_rejects_invalid_wireguard_key_and_peer_shapes() -> None:
    errors = validate_xray_config(
        {
            "outbounds": [
                {
                    "tag": "warp",
                    "protocol": "wireguard",
                    "settings": {
                        "secretKey": "",
                        "address": [""],
                        "peers": [{"endpoint": 42, "publicKey": ""}],
                    },
                }
            ]
        }
    )

    assert "xray.json outbounds[0] missing wireguard secretKey" in errors
    assert (
        "xray.json outbounds[0] wireguard address must be a non-empty string list"
        in errors
    )
    assert "xray.json outbounds[0] wireguard peers[0] missing endpoint" in errors
    assert "xray.json outbounds[0] wireguard peers[0] missing publicKey" in errors


def test_nekobox_subscription_roundtrip(tmp_path: Path) -> None:
    text = "vless://example.com#node\n"
    (tmp_path / "proxies.txt").write_text(text, encoding="utf-8")
    (tmp_path / "base64.txt").write_text(
        base64.b64encode(text.encode("utf-8")).decode("ascii"), encoding="utf-8"
    )
    assert validate_nekobox_subscriptions(tmp_path) == []


def test_output_matrix_declares_xray_contract() -> None:
    matrix_path = Path(__file__).resolve().parents[2] / "docs" / "output_matrix.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    xray = next(item for item in matrix["outputs"] if item["path"] == "xray.json")
    assert xray["core_format"] == "xray"
    assert xray["artifact_type"] == "full_config"
