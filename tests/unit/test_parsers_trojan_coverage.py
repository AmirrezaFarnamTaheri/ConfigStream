
import pytest
from src.configstream.parsers.trojan import parse_trojan
from src.configstream.models import Proxy
from unittest.mock import patch

def test_parse_trojan_valid():
    config = "trojan://uuid@1.1.1.1:443?sni=google.com#MyTrojan"
    p = parse_trojan(config)
    assert p.protocol == "trojan"
    assert p.address == "1.1.1.1"
    assert p.port == 443
    assert p.uuid == "uuid"
    assert p.details["sni"] == "google.com"
    assert p.remarks == "MyTrojan"

def test_parse_trojan_invalid_scheme():
    assert parse_trojan("http://1.1.1.1") is None

def test_parse_trojan_invalid_host():
    # hostname required
    assert parse_trojan("trojan://") is None
    # too long
    long_host = "a" * 256
    assert parse_trojan(f"trojan://uuid@{long_host}") is None

def test_parse_trojan_port_zero():
    # Port 0 becomes default 443 due to 'or 443' behavior with falsy 0
    p = parse_trojan("trojan://uuid@1.1.1.1:0")
    assert p is not None
    assert p.port == 443

def test_parse_trojan_port_too_high():
    # Port > 65535
    assert parse_trojan("trojan://uuid@1.1.1.1:65536") is None

def test_parse_trojan_exception():
    with patch("src.configstream.parsers.trojan.urlparse") as mock_parse:
        mock_parse.side_effect = ValueError("Boom")
        assert parse_trojan("trojan://test") is None
