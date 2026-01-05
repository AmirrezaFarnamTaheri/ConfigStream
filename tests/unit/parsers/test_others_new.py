# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from configstream.parsers.others import parse_wireguard, parse_hysteria2


def test_wireguard_missing_keys():
    """Test WireGuard parsing with missing keys"""
    # Invalid config (no private key or uuid)
    config = "wireguard://example.com:51820"
    assert parse_wireguard(config) is None

    # Valid config (uuid as private key)
    config_valid = "wireguard://privatekey@example.com:51820"
    proxy = parse_wireguard(config_valid)
    assert proxy is not None
    assert proxy.details["private_key"] == "privatekey"


def test_hysteria2_obfs():
    """Test Hysteria2 obfuscation handling"""
    # Valid with obfs
    config = "hysteria2://pass@example.com:443?obfs=salamander&obfs-password=secret"
    proxy = parse_hysteria2(config)
    assert proxy is not None
    assert proxy.details["obfs"] == "salamander"
    assert proxy.details["obfs-password"] == "secret"

    # Missing obfs password (should drop proxy)
    config_missing = "hysteria2://pass@example.com:443?obfs=salamander"
    proxy = parse_hysteria2(config_missing)
    assert proxy is None
