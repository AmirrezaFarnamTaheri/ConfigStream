
import pytest
from src.configstream.parsers.vless import parse_vless
from src.configstream.models import Proxy
from unittest.mock import patch

def test_parse_vless_valid():
    config = "vless://uuid@1.1.1.1:443?security=tls&sni=google.com#MyVLESS"
    p = parse_vless(config)
    assert p.protocol == "vless"
    assert p.address == "1.1.1.1"
    assert p.port == 443
    assert p.uuid == "uuid"
    assert p.details["security"] == "tls"
    assert p.remarks == "MyVLESS"

def test_parse_vless_invalid_host():
    assert parse_vless("vless://uuid@:443") is None
    # hostname too long
    long_host = "a" * 256
    assert parse_vless(f"vless://uuid@{long_host}:443") is None

def test_parse_vless_port_zero():
    # Port 0 -> default 443
    p = parse_vless("vless://uuid@1.1.1.1:0")
    assert p is not None
    assert p.port == 443

def test_parse_vless_port_too_high():
    assert parse_vless("vless://uuid@1.1.1.1:65536") is None

def test_parse_vless_invalid_uuid():
    # empty uuid
    assert parse_vless("vless://1.1.1.1:443") is None
    # too long uuid
    long_uuid = "a" * 101
    assert parse_vless(f"vless://{long_uuid}@1.1.1.1:443") is None

def test_parse_vless_reality_checks():
    # Valid reality
    config = "vless://uuid@1.1.1.1:443?security=reality&pbk=key&sid=id"
    assert parse_vless(config) is not None

    # Missing pbk
    config = "vless://uuid@1.1.1.1:443?security=reality&sid=id"
    assert parse_vless(config) is None

    # Missing sid
    config = "vless://uuid@1.1.1.1:443?security=reality&pbk=key"
    assert parse_vless(config) is None

def test_parse_vless_exception():
    with patch("src.configstream.parsers.vless.urlparse") as mock_parse:
        mock_parse.side_effect = ValueError("Boom")
        assert parse_vless("vless://test") is None
