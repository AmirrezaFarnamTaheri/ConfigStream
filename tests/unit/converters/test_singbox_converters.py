# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from configstream.models import Proxy
from configstream.converters.singbox import to_singbox_outbound


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
    # Check IP format
    assert out1["local_address"][0].startswith("172.16.")
    # Different private keys should produce different IPs
    assert out1["local_address"][0] != out2["local_address"][0]

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
    assert out1["local_address"][0] == out3["local_address"][0]
