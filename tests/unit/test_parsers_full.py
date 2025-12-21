from configstream.parsers.generic import (
    parse_generic_url_scheme as _parse_generic_url_scheme,
)
from configstream.parsers.ssr import parse_ssr
from configstream.parsers.trojan import parse_trojan
from configstream.parsers.vless import parse_vless
from configstream.parsers.vmess import parse_vmess
import base64
import json


def test_parse_generic_fallback():
    # Invalid line
    try:
        p = _parse_generic_url_scheme("invalid line")
        assert p is None
    except ValueError:
        pass


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
        "vless://123e4567-e89b-12d3-a456-426614174000@1.1.1.1:443?encryption=none&security=tls&sni=example.com#Test"
    )
    assert p is not None
    assert p.protocol == "vless"


def test_parse_vmess_valid():
    # vmess is typically base64 encoded json
    v_obj = {
        "v": "2",
        "ps": "Test",
        "add": "1.1.1.1",
        "port": 443,
        "id": "uuid",
        "aid": 0,
        "net": "ws",
        "type": "none",
        "host": "example.com",
        "path": "/path",
        "tls": "tls",
    }
    b64 = base64.b64encode(json.dumps(v_obj).encode()).decode()
    uri = f"vmess://{b64}"

    p = parse_vmess(uri)
    assert p is not None
    assert p.protocol == "vmess"
    assert p.address == "1.1.1.1"
    assert p.uuid == "uuid"
    assert p.details["net"] == "ws"
