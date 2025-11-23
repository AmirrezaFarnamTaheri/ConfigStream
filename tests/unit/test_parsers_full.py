import pytest
from configstream.parsers.generic import parse_generic_url_scheme
from configstream.parsers.ssr import parse_ssr
from configstream.parsers.trojan import parse_trojan
from configstream.parsers.vless import parse_vless
from configstream.parsers.vmess import parse_vmess
from configstream.models import Proxy


def test_parse_generic_fallback():
    # Invalid line
    p = parse_generic_url_scheme("invalid line")
    assert p is None


def test_parse_ssr_invalid():
    p = parse_ssr("ssr://invalid")
    assert p is None


def test_parse_trojan_valid():
    p = parse_trojan("trojan://password@1.1.1.1:443?sni=example.com#Test")
    assert p is not None
    assert p.protocol == "trojan"
    assert p.address == "1.1.1.1"


def test_parse_vless_valid():
    p = parse_vless(
        "vless://uuid@1.1.1.1:443?encryption=none&security=tls&sni=example.com#Test"
    )
    assert p is not None
    assert p.protocol == "vless"


def test_parse_vmess_valid():
    pass
