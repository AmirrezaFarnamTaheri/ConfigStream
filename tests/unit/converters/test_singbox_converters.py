# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.models import Proxy
from configstream.converters.singbox import (
    to_singbox_outbound,
    VALID_SS_METHODS,
    VALID_VLESS_FLOWS,
    _sanitize_ss_method,
    _sanitize_vless_flow,
)


def test_singbox_vless_missing_uuid():
    """Test VLESS conversion with missing UUID logs warning and returns None"""
    proxy = Proxy(
        config="vless://example.com:443",
        protocol="vless",
        address="example.com",
        port=443,
        uuid="",  # Missing
        remarks="test",
    )
    # Mocking logger is tricky in unit test without fixtures, but we can check return None
    assert to_singbox_outbound(proxy) is None


def test_singbox_trojan_conversion():
    """Test standard Trojan conversion"""
    proxy = Proxy(
        config="trojan://pass@example.com:443",
        protocol="trojan",
        address="example.com",
        port=443,
        uuid="pass",
        remarks="test",
        details={"tls": "tls"},
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["type"] == "trojan"
    assert out["password"] == "pass"
    assert out["tls"]["enabled"] is True


def test_singbox_wireguard_unique_ip():
    """Test WireGuard local IP generation based on private key"""
    # Test 1: Different private keys should produce different IPs
    proxy1 = Proxy(
        config="wireguard://example.com:51820",
        protocol="wireguard",
        address="example.com",
        port=51820,
        uuid="private_key_1",
        details={"private_key": "private_key_1", "peer_public_key": "pub"},
    )
    proxy2 = Proxy(
        config="wireguard://example.org:51820",
        protocol="wireguard",
        address="example.org",
        port=51820,
        uuid="private_key_2",
        details={"private_key": "private_key_2", "peer_public_key": "pub"},
    )

    out1 = to_singbox_outbound(proxy1)
    out2 = to_singbox_outbound(proxy2)

    assert out1 is not None
    assert out2 is not None
    # Check IP format (Sing-box now expects string, not list)
    assert isinstance(out1["local_address"], str)
    assert out1["local_address"].startswith("172.16.")
    # Different private keys should produce different IPs
    assert out1["local_address"] != out2["local_address"]

    # Test 2: Same private key but different endpoints should produce SAME IP
    proxy3 = Proxy(
        config="wireguard://different-endpoint.com:51820",
        protocol="wireguard",
        address="different-endpoint.com",
        port=51820,
        uuid="private_key_1",
        details={"private_key": "private_key_1", "peer_public_key": "pub"},
    )
    out3 = to_singbox_outbound(proxy3)
    assert out3 is not None
    # Same private key should produce same IP (collision prevention)
    assert out1["local_address"] == out3["local_address"]


# --- New tests for schema alignment fixes ---


def test_ss_method_whitelist_schema_compliance():
    """Verify VALID_SS_METHODS matches sing-box schema."""
    # These must be in the whitelist (per sing-box schema)
    assert "aes-128-gcm" in VALID_SS_METHODS
    assert "aes-256-gcm" in VALID_SS_METHODS
    assert "chacha20-ietf-poly1305" in VALID_SS_METHODS
    assert "xchacha20-ietf-poly1305" in VALID_SS_METHODS
    assert "2022-blake3-aes-128-gcm" in VALID_SS_METHODS
    assert "2022-blake3-aes-256-gcm" in VALID_SS_METHODS
    assert "2022-blake3-chacha20-poly1305" in VALID_SS_METHODS
    assert "none" in VALID_SS_METHODS
    # These must NOT be in the whitelist (not in sing-box schema)
    assert "chacha20" not in VALID_SS_METHODS
    assert "plain" not in VALID_SS_METHODS


def test_ss_method_alias_mapping():
    """Test that removed methods map to valid aliases."""
    # "plain" -> "none"
    assert _sanitize_ss_method("plain") == "none"
    # "chacha20" -> "chacha20-ietf-poly1305" (Updated expectation)
    assert _sanitize_ss_method("chacha20") == "chacha20-ietf-poly1305"
    # "auto" -> "chacha20-ietf-poly1305"
    assert _sanitize_ss_method("auto") == "chacha20-ietf-poly1305"
    # Garbage should return None
    assert _sanitize_ss_method("un;k") is None
    assert _sanitize_ss_method("}k") is None


def test_vless_flow_schema_compliance():
    """Verify VALID_VLESS_FLOWS matches sing-box schema."""
    assert "" in VALID_VLESS_FLOWS
    assert "xtls-rprx-vision" in VALID_VLESS_FLOWS
    # Removed: not in sing-box schema
    assert "xtls-rprx-vision-udp443" not in VALID_VLESS_FLOWS


def test_vless_flow_sanitization():
    """Test that invalid/unsupported flows are stripped."""
    assert _sanitize_vless_flow("xtls-rprx-vision") == "xtls-rprx-vision"
    assert _sanitize_vless_flow("") == ""
    assert _sanitize_vless_flow(None) == ""
    # Unsupported flows should be stripped to ""
    assert _sanitize_vless_flow("xtls-rprx-direct") == ""
    assert _sanitize_vless_flow("xtls-rprx-splice") == ""
    # Unknown flows should be stripped to ""
    assert _sanitize_vless_flow("xtls-rprx-vision-udp443") == ""


def test_httpupgrade_transport():
    """Test httpupgrade transport support (per sing-box schema)."""
    proxy = Proxy(
        config="vless://uuid@example.com:443",
        protocol="vless",
        address="example.com",
        port=443,
        uuid="test-uuid-1234",
        details={
            "net": "httpupgrade",
            "path": "/upgrade",
            "host": "cdn.example.com",
            "tls": "tls",
        },
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["transport"]["type"] == "httpupgrade"
    assert out["transport"]["path"] == "/upgrade"
    assert out["transport"]["host"] == "cdn.example.com"


def test_vless_packet_encoding():
    """Test that VLESS gets default packet_encoding=xudp."""
    proxy = Proxy(
        config="vless://uuid@example.com:443",
        protocol="vless",
        address="example.com",
        port=443,
        uuid="test-uuid-1234",
        details={"tls": "tls"},
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out.get("packet_encoding") == "xudp"


def test_tuic_udp_relay_mode():
    """Test TUIC udp_relay_mode per sing-box schema."""
    proxy = Proxy(
        config="tuic://example.com:443",
        protocol="tuic",
        address="example.com",
        port=443,
        uuid="test-uuid",
        details={"password": "pass", "udp_relay_mode": "native", "sni": "example.com"},
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["udp_relay_mode"] == "native"


def test_socks4a_support():
    """Test socks4a version support per sing-box schema."""
    proxy = Proxy(
        config="socks4a://example.com:1080",
        protocol="socks4a",
        address="example.com",
        port=1080,
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["version"] == "4a"


def test_ssh_host_key_as_array():
    """Test that SSH host_key is emitted as array per sing-box schema."""
    proxy = Proxy(
        config="ssh://user@example.com:22",
        protocol="ssh",
        address="example.com",
        port=22,
        uuid="root",
        details={"password": "pass", "host_key": "ssh-rsa AAAA..."},
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert isinstance(out["host_key"], list)
    assert len(out["host_key"]) == 1


def test_wireguard_pre_shared_key():
    """Test WireGuard pre_shared_key support per sing-box schema."""
    proxy = Proxy(
        config="wireguard://example.com:51820",
        protocol="wireguard",
        address="example.com",
        port=51820,
        details={
            "private_key": "private_key_1",
            "peer_public_key": "pub",
            "pre_shared_key": "psk_key_value",
            "mtu": "1400",
        },
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["pre_shared_key"] == "psk_key_value"
    assert out["mtu"] == 1400


def test_singbox_outbounds_validate_against_schema():
    """Verify that generated sing-box outbounds match our schema draft."""
    import pytest

    jsonschema = pytest.importorskip("jsonschema")
    import json
    from pathlib import Path

    schema_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "schema"
        / "singbox_outbound.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    proxies = [
        # VLESS
        Proxy(
            config="vless://88888888-4444-4444-4444-121212121212@example.com:443",
            protocol="vless",
            address="example.com",
            port=443,
            uuid="88888888-4444-4444-4444-121212121212",
            details={"tls": "tls"},
        ),
        # VMess
        Proxy(
            config="vmess://88888888-4444-4444-4444-121212121212@example.com:443",
            protocol="vmess",
            address="example.com",
            port=443,
            uuid="88888888-4444-4444-4444-121212121212",
        ),
        # Trojan
        Proxy(
            config="trojan://pass@example.com:443",
            protocol="trojan",
            address="example.com",
            port=443,
            uuid="pass",
        ),
        # Shadowsocks
        Proxy(
            config="ss://aes-256-gcm:pass@example.com:443",
            protocol="shadowsocks",
            address="example.com",
            port=443,
            uuid="aes-256-gcm:pass",
            details={"method": "aes-256-gcm", "password": "pass"},
        ),
        # Hysteria2
        Proxy(
            config="hysteria2://pass@example.com:443",
            protocol="hysteria2",
            address="example.com",
            port=443,
            uuid="pass",
        ),
        # Tuic
        Proxy(
            config="tuic://uuid:pass@example.com:443",
            protocol="tuic",
            address="example.com",
            port=443,
            uuid="uuid",
            details={"password": "pass"},
        ),
        # WireGuard
        Proxy(
            config="wg://example.com:51820",
            protocol="wireguard",
            address="example.com",
            port=51820,
            details={"private_key": "privatekey==", "peer_public_key": "pubkey=="},
        ),
    ]

    for p in proxies:
        out = to_singbox_outbound(p)
        assert out is not None, f"Conversion failed for {p.protocol}"
        validator.validate(out)
