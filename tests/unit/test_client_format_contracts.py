# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for cross-client format contracts."""

from __future__ import annotations

import base64
import json
import pytest
from pathlib import Path

from configstream.models import Proxy

from configstream.output.client_formats import (
    generate_nekobox_json_subscription,
    generate_xray_config,
    validate_mihomo_config,
    validate_nekobox_json_subscription,
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


def test_singbox_endpoint_only_config_is_valid_reference_surface() -> None:
    payload = {
        "endpoints": [
            {
                "type": "wireguard",
                "tag": "warp",
                "address": ["172.16.0.2/32"],
                "private_key": "QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE=",
                "peers": [
                    {
                        "address": "162.159.192.1",
                        "port": 2408,
                        "public_key": "QkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkI=",
                        "allowed_ips": ["0.0.0.0/0"],
                    }
                ],
            }
        ],
        "route": {"final": "warp"},
    }

    assert validate_singbox_config(payload, "endpoint-only.json") == []


def test_singbox_requires_at_least_one_outbound_or_endpoint() -> None:
    assert validate_singbox_config(
        {"outbounds": [], "endpoints": []}, "empty.json"
    ) == ["empty.json must define at least one outbound or endpoint"]


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


def test_xray_wireguard_normalizes_ipv6_endpoint_and_keepalive() -> None:
    config, report = generate_xray_config(
        [
            {
                "id": "wg-v6",
                "protocol": "wireguard",
                "address": "2606:4700:d0::a29f:c001",
                "port": 2408,
                "remarks": "wg-v6",
                "is_working": True,
                "details": {
                    "private_key": "00" * 32,
                    "peer_public_key": "11" * 32,
                    "local_address": ["172.16.0.2/32"],
                    "allowed_ips": ["0.0.0.0/0", "::/0"],
                    "persistent_keepalive_interval": "30",
                    "mtu": "1280",
                },
            }
        ]
    )

    outbound = config["outbounds"][0]
    peer = outbound["settings"]["peers"][0]
    assert peer["endpoint"] == "[2606:4700:d0::a29f:c001]:2408"
    assert peer["keepAlive"] == 30
    assert outbound["settings"]["mtu"] == 1280
    assert report["emitted_records"] == 1


def test_xray_wireguard_preserves_multiple_validated_peers() -> None:
    endpoint = {
        "type": "wireguard",
        "tag": "wg-multi",
        "address": ["172.16.0.2/32"],
        "private_key": "00" * 32,
        "peers": [
            {
                "address": "162.159.192.1",
                "port": 2408,
                "public_key": "11" * 32,
                "allowed_ips": ["0.0.0.0/1"],
                "reserved": [1, 2, 3],
            },
            {
                "address": "2606:4700:d0::a29f:c001",
                "port": 2408,
                "public_key": "22" * 32,
                "allowed_ips": ["128.0.0.0/1", "::/0"],
                "reserved": [1, 2, 3],
            },
        ],
    }
    config, report = generate_xray_config(
        [
            {
                "id": "multi-peer-chain",
                "protocol": "chain",
                "is_working": True,
                "config": json.dumps({"outbounds": [], "endpoints": [endpoint]}),
            }
        ]
    )

    settings = config["outbounds"][0]["settings"]
    assert len(settings["peers"]) == 2
    assert settings["peers"][1]["endpoint"] == "[2606:4700:d0::a29f:c001]:2408"
    assert settings["reserved"] == [1, 2, 3]
    assert report["emitted_records"] == 1


def test_xray_wireguard_drops_unrepresentable_peer_reserved_conflict() -> None:
    endpoint = {
        "type": "wireguard",
        "tag": "wg-conflict",
        "address": ["172.16.0.2/32"],
        "private_key": "00" * 32,
        "peers": [
            {
                "address": "162.159.192.1",
                "port": 2408,
                "public_key": "11" * 32,
                "allowed_ips": ["0.0.0.0/1"],
                "reserved": [1, 2, 3],
            },
            {
                "address": "162.159.192.2",
                "port": 2408,
                "public_key": "22" * 32,
                "allowed_ips": ["128.0.0.0/1"],
                "reserved": [3, 2, 1],
            },
        ],
    }
    config, report = generate_xray_config(
        [
            {
                "id": "reserved-conflict",
                "protocol": "chain",
                "is_working": True,
                "config": json.dumps({"outbounds": [], "endpoints": [endpoint]}),
            }
        ]
    )

    assert [item["tag"] for item in config["outbounds"]] == ["direct", "block"]
    assert report["unsupported"] == {"chain": 1}


@pytest.mark.parametrize(
    ("field", "value"),
    [("mtu", "invalid"), ("persistent_keepalive_interval", "invalid")],
)
def test_xray_wireguard_drops_malformed_numeric_metadata(
    field: str, value: object
) -> None:
    details: dict[str, object] = {
        "private_key": "00" * 32,
        "peer_public_key": "11" * 32,
        "local_address": ["172.16.0.2/32"],
        "allowed_ips": ["0.0.0.0/0"],
        "mtu": "1280",
        "persistent_keepalive_interval": "30",
    }
    details[field] = value
    config, report = generate_xray_config(
        [
            {
                "id": "bad-wg",
                "protocol": "wireguard",
                "address": "162.159.192.1",
                "port": 2408,
                "is_working": True,
                "details": details,
            }
        ]
    )

    assert [item["tag"] for item in config["outbounds"]] == ["direct", "block"]
    assert report["unsupported"] == {"wireguard": 1}


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


def test_xray_drops_plain_trojan_to_public_ip() -> None:
    """Xray >= 26.7 refuses no-TLS trojan to public IPs at config-build time.

    Run 32638423498 failed native-validation on exactly this: a working
    plain-TCP trojan record made xray.json unrunnable, blocking the release
    gate. Such records must be excluded instead of emitted.
    """
    config, report = generate_xray_config(
        [
            {
                "id": "t1",
                "protocol": "trojan",
                "address": "93.184.216.34",  # public IP literal
                "port": 443,
                "uuid": "pw1",
                "remarks": "trojan-plain-ip",
                "is_working": True,
                "details": {},
            },
            {
                "id": "t2",
                "protocol": "trojan",
                "address": "93.184.216.35",
                "port": 443,
                "uuid": "pw2",
                "remarks": "trojan-tls",
                "is_working": True,
                "details": {"tls": True, "sni": "example.com"},
            },
            {
                "id": "t3",
                "protocol": "trojan",
                "address": "proxy.example.net",  # public domains require TLS too
                "port": 443,
                "uuid": "pw3",
                "remarks": "trojan-domain",
                "is_working": True,
                "details": {},
            },
        ]
    )
    tags = [outbound["tag"] for outbound in config["outbounds"]]
    assert "trojan-plain-ip" not in tags
    assert "trojan-tls" in tags
    assert "trojan-domain" not in tags
    assert report["unsupported"].get("trojan") == 2
    assert validate_xray_config(config) == []


@pytest.mark.parametrize("protocol", ["trojan", "vless"])
@pytest.mark.parametrize(
    "address", ["relay.example.net", "93.184.216.34", "2606:4700::1111"]
)
def test_xray_rejects_public_plaintext_destinations(
    protocol: str, address: str
) -> None:
    record = {
        "protocol": protocol,
        "address": address,
        "port": 443,
        "uuid": "00000000-0000-0000-0000-000000000001",
        "is_working": True,
        "details": {},
    }
    config, report = generate_xray_config([record])
    assert report["emitted_records"] == 0
    assert [outbound["tag"] for outbound in config["outbounds"]] == ["direct", "block"]
    # Structural validation must also reject imported/previously generated configs.
    config["outbounds"].insert(
        0,
        {
            "tag": "unsafe",
            "protocol": protocol,
            "settings": {
                "address": address,
                "port": 443,
                "password": "fixture",
                "id": record["uuid"],
            },
            "streamSettings": {"method": "raw", "rawSettings": {}, "security": "none"},
        },
    )
    assert any(
        "public destinations require" in error for error in validate_xray_config(config)
    )


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "100.64.0.1",
        "192.0.2.1",
        "::1",
        "fd00::1",
        "relay.local",
        "HOME.ARPA.",
        "router",
    ],
)
def test_xray_preserves_supported_private_plaintext_destinations(address: str) -> None:
    config, report = generate_xray_config(
        [
            {
                "protocol": "trojan",
                "address": address,
                "port": 443,
                "uuid": "fixture",
                "is_working": True,
                "details": {},
            }
        ]
    )
    assert report["emitted_records"] == 1
    assert validate_xray_config(config) == []


def test_xray_excludes_entire_chain_if_a_hop_is_incompatible() -> None:
    config, report = generate_xray_config(
        [
            {
                "protocol": "chain",
                "is_working": True,
                "config": json.dumps(
                    {
                        "outbounds": [
                            {
                                "tag": "relay",
                                "type": "trojan",
                                "server": "relay.example.net",
                                "server_port": 443,
                                "password": "fixture",
                            },
                            {
                                "tag": "exit",
                                "type": "socks",
                                "server": "exit.example.net",
                                "server_port": 1080,
                                "detour": "relay",
                            },
                        ]
                    }
                ),
            }
        ]
    )
    assert report["unsupported"] == {"chain": 1}
    assert [outbound["tag"] for outbound in config["outbounds"]] == ["direct", "block"]
    assert validate_xray_config(config) == []


def test_xray_tls_settings_omit_removed_allow_insecure() -> None:
    """Xray >= 26.7 removed allowInsecure and refuses configs carrying it.

    Run 32653192568 failed native-validation because chain hops exported
    their tested `insecure` flag into xray.json tlsSettings, making one hop
    invalidate the whole file. The generated export must never emit it.
    """
    config, report = generate_xray_config(
        [
            {
                "id": "n1",
                "protocol": "vless",
                "address": "93.184.216.34",
                "port": 443,
                "uuid": "00000000-0000-0000-0000-00000000abc1",
                "remarks": "insecure-vless",
                "is_working": True,
                "details": {"tls": True, "sni": "example.com", "allowInsecure": True},
            }
        ]
    )
    outbound = next(o for o in config["outbounds"] if o.get("tag") == "insecure-vless")
    assert "allowInsecure" not in outbound["streamSettings"]["tlsSettings"]
    assert validate_xray_config(config) == []
    assert report["emitted_records"] == 1


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


@pytest.mark.parametrize("value", [[], {}])
def test_xray_rejects_non_scalar_protocol_and_stream_fields(value: object) -> None:
    errors = validate_xray_config(
        {
            "outbounds": [
                {"tag": "bad", "protocol": value, "settings": {}},
                {
                    "tag": "plain",
                    "protocol": "trojan",
                    "settings": {
                        "address": "public.example.com",
                        "port": 443,
                        "password": "test",
                    },
                    "streamSettings": {"method": value, "security": value},
                },
            ]
        }
    )
    assert "xray.json outbounds[0] missing protocol" in errors
    assert "xray.json outbounds[1] has invalid streamSettings.method" in errors
    assert any("public destinations require TLS" in error for error in errors)


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


def test_nekobox_json_subscription_uses_minimal_node_container() -> None:
    proxies = [
        Proxy(
            config="vless://00000000-0000-0000-0000-000000000001@example.com:443#node-a",
            protocol="vless",
            address="example.com",
            port=443,
            uuid="00000000-0000-0000-0000-000000000001",
            remarks="node-a",
            is_working=True,
            details={"security": "tls", "sni": "example.com"},
        ),
        Proxy(
            config="vless://00000000-0000-0000-0000-000000000002@example.net:443#node-b",
            protocol="vless",
            address="example.net",
            port=443,
            uuid="00000000-0000-0000-0000-000000000002",
            remarks="node-b",
            is_working=True,
            details={"security": "tls", "sni": "example.net"},
        ),
    ]

    payload = json.loads(generate_nekobox_json_subscription(proxies))

    assert set(payload) == {"outbounds", "endpoints"}
    assert [item["tag"] for item in payload["outbounds"]] == ["node-a", "node-b"]
    assert payload["endpoints"] == []
    assert all(item["type"] == "vless" for item in payload["outbounds"])
    assert all("detour" not in item for item in payload["outbounds"])
    assert validate_nekobox_json_subscription(payload) == []


def test_nekobox_json_subscription_excludes_nonworking_nodes() -> None:
    working = Proxy(
        config="vless://00000000-0000-0000-0000-000000000001@example.com:443#working",
        protocol="vless",
        address="example.com",
        port=443,
        uuid="00000000-0000-0000-0000-000000000001",
        remarks="working",
        is_working=True,
        details={"security": "tls", "sni": "example.com"},
    )
    failed = Proxy(
        config="vless://00000000-0000-0000-0000-000000000002@example.net:443#failed",
        protocol="vless",
        address="example.net",
        port=443,
        uuid="00000000-0000-0000-0000-000000000002",
        remarks="failed",
        is_working=False,
        details={"security": "tls", "sni": "example.net"},
    )

    payload = json.loads(generate_nekobox_json_subscription([failed, working]))

    assert [item["tag"] for item in payload["outbounds"]] == ["working"]
    assert payload["endpoints"] == []


def test_nekobox_json_subscription_is_empty_when_no_nodes_are_working() -> None:
    failed = Proxy(
        config="vless://00000000-0000-0000-0000-000000000003@example.org:443#failed",
        protocol="vless",
        address="example.org",
        port=443,
        uuid="00000000-0000-0000-0000-000000000003",
        remarks="failed",
        is_working=False,
        details={"security": "tls", "sni": "example.org"},
    )

    payload = json.loads(generate_nekobox_json_subscription([failed]))

    assert payload == {"outbounds": [], "endpoints": []}
    assert validate_nekobox_json_subscription(payload) == []


def test_nekobox_json_subscription_rejects_raw_root_array() -> None:
    errors = validate_nekobox_json_subscription([{"type": "vless", "tag": "node"}])

    assert errors == [
        "nekobox.json must be a JSON object containing outbounds/endpoints arrays"
    ]


def test_nekobox_json_subscription_rejects_full_profile_keys() -> None:
    errors = validate_nekobox_json_subscription(
        {
            "outbounds": [{"type": "vless", "tag": "node"}],
            "endpoints": [],
            "route": {"final": "node"},
        }
    )

    assert any("unsupported top-level keys: route" in error for error in errors)


def test_nekobox_json_subscription_rejects_helper_and_detour_nodes() -> None:
    errors = validate_nekobox_json_subscription(
        {
            "outbounds": [
                {"type": "selector", "tag": "group", "outbounds": ["node"]},
                {"type": "vless", "tag": "node", "detour": "relay"},
            ],
            "endpoints": [],
        }
    )

    assert any("helper type selector" in error for error in errors)
    assert any("has detour" in error for error in errors)


def test_nekobox_json_subscription_modernizes_wireguard_to_endpoint() -> None:
    private_key = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    public_key = "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE="
    proxy = Proxy(
        config=f"wireguard://{private_key}@162.159.192.1:2408#warp",
        protocol="wireguard",
        address="162.159.192.1",
        port=2408,
        remarks="warp",
        is_working=True,
        details={
            "private_key": private_key,
            "peer_public_key": public_key,
            "local_address": ["10.0.0.2/32"],
            "allowed_ips": ["0.0.0.0/0"],
            "mtu": 1280,
        },
    )

    payload = json.loads(generate_nekobox_json_subscription([proxy]))

    assert payload["outbounds"] == []
    assert len(payload["endpoints"]) == 1
    endpoint = payload["endpoints"][0]
    assert endpoint["type"] == "wireguard"
    assert endpoint["tag"] == "warp"
    assert endpoint["address"] == ["10.0.0.2/32"]
    assert endpoint["peers"][0]["address"] == "162.159.192.1"
    assert endpoint["peers"][0]["port"] == 2408
    assert validate_nekobox_json_subscription(payload) == []


def test_nekobox_json_subscription_rejects_legacy_wireguard_outbound() -> None:
    errors = validate_nekobox_json_subscription(
        {
            "outbounds": [{"type": "wireguard", "tag": "legacy"}],
            "endpoints": [],
        }
    )

    assert any("legacy WireGuard outbound shape" in error for error in errors)


def test_xray_chain_uses_sockopt_dialer_proxy() -> None:
    config, report = generate_xray_config(
        [
            {
                "id": "chain-modern",
                "protocol": "chain",
                "is_working": True,
                "config": json.dumps(
                    {
                        "outbounds": [
                            {
                                "tag": "relay",
                                "type": "socks",
                                "server": "127.0.0.1",
                                "server_port": 1080,
                            },
                            {
                                "tag": "exit",
                                "type": "socks",
                                "server": "127.0.0.1",
                                "server_port": 1081,
                                "detour": "relay",
                            },
                        ]
                    }
                ),
            }
        ]
    )

    assert report["emitted_records"] == 1
    exit_outbound = next(item for item in config["outbounds"] if item["tag"] == "exit")
    assert "proxySettings" not in exit_outbound
    assert exit_outbound["streamSettings"]["sockopt"]["dialerProxy"] == "relay"
    assert validate_xray_config(config) == []


def test_xray_validator_rejects_removed_proxy_settings() -> None:
    errors = validate_xray_config(
        {
            "outbounds": [
                {
                    "tag": "legacy-chain",
                    "protocol": "socks",
                    "settings": {"address": "127.0.0.1", "port": 1080},
                    "streamSettings": {
                        "method": "raw",
                        "rawSettings": {},
                        "security": "none",
                    },
                    "proxySettings": {
                        "tag": "direct",
                        "transportLayer": True,
                    },
                },
                {"tag": "direct", "protocol": "freedom", "settings": {}},
                {"tag": "block", "protocol": "blackhole", "settings": {}},
            ]
        }
    )

    assert any("uses removed proxySettings" in error for error in errors)


def test_xray_validator_checks_dialer_proxy_references() -> None:
    errors = validate_xray_config(
        {
            "outbounds": [
                {
                    "tag": "node",
                    "protocol": "socks",
                    "settings": {"address": "127.0.0.1", "port": 1080},
                    "streamSettings": {
                        "method": "raw",
                        "rawSettings": {},
                        "security": "none",
                        "sockopt": {"dialerProxy": "missing"},
                    },
                },
                {"tag": "direct", "protocol": "freedom", "settings": {}},
                {"tag": "block", "protocol": "blackhole", "settings": {}},
            ]
        }
    )

    assert any(
        "streamSettings.sockopt.dialerProxy references unknown tag: missing" in error
        for error in errors
    )


def test_xray_drops_legacy_h2_instead_of_relabeling_as_xhttp() -> None:
    config, report = generate_xray_config(
        [
            {
                "id": "legacy-h2",
                "protocol": "vless",
                "address": "93.184.216.34",
                "port": 443,
                "uuid": "00000000-0000-0000-0000-00000000f001",
                "remarks": "legacy-h2",
                "is_working": True,
                "details": {
                    "security": "tls",
                    "sni": "example.com",
                    "net": "h2",
                    "path": "/legacy",
                    "host": "example.com",
                },
            }
        ]
    )

    assert report["emitted_records"] == 0
    assert report["unsupported"] == {"vless": 1}
    assert [item["tag"] for item in config["outbounds"]] == ["direct", "block"]


def test_xray_preserves_explicit_xhttp_transport() -> None:
    config, report = generate_xray_config(
        [
            {
                "id": "modern-xhttp",
                "protocol": "vless",
                "address": "93.184.216.34",
                "port": 443,
                "uuid": "00000000-0000-0000-0000-00000000f002",
                "remarks": "modern-xhttp",
                "is_working": True,
                "details": {
                    "security": "tls",
                    "sni": "example.com",
                    "net": "xhttp",
                    "path": "/modern",
                    "host": "example.com",
                },
            }
        ]
    )

    outbound = next(
        item for item in config["outbounds"] if item["tag"] == "modern-xhttp"
    )
    assert outbound["streamSettings"]["method"] == "xhttp"
    assert outbound["streamSettings"]["xhttpSettings"]["path"] == "/modern"
    assert report["emitted_records"] == 1
    assert validate_xray_config(config) == []


def test_singbox_contract_rejects_removed_public_outbound_shapes() -> None:
    payload = {
        "outbounds": [
            {"type": "block", "tag": "block"},
            {"type": "dns", "tag": "dns-out"},
            {
                "type": "wireguard",
                "tag": "warp",
                "server": "162.159.192.1",
                "server_port": 2408,
            },
            {"type": "direct", "tag": "direct"},
        ],
        "route": {"final": "direct", "rules": []},
    }

    errors = validate_singbox_config(payload, "singbox.json")

    assert any("legacy block outbound shape" in error for error in errors)
    assert any("legacy dns outbound shape" in error for error in errors)
    assert any("legacy wireguard outbound shape" in error for error in errors)
