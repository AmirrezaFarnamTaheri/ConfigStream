import pytest
from configstream.parsers import (
    _parse_ssr,
    _parse_v2ray_json,
    _parse_hysteria,
    _parse_hysteria2,
    _parse_tuic,
)


def test_parse_ssr_with_invalid_base64():
    """Test that _parse_ssr handles invalid base64 in the main part."""
    config = "ssr://invalid-base64"
    assert _parse_ssr(config) is None


def test_parse_ssr_with_invalid_base64_in_params():
    """Test that _parse_ssr handles invalid base64 in the parameters."""
    config = (
        "ssr://anUtdHQuY29tOjQ0MzphdXRoX2FlczEyOF9tZDU6YWVzLTI1Ni1jZmI6dGxzMS4yX3RpY2tldF9hdXRoO"
        "lFYVjNZWEJwYnk1amJ5NWpiMjB2ZFc1a1lYQnBiV0Z6ZEdWeWMybHZiajB4T0RBd01EQXdNREF3TURBd01EQXdNQS8"
        "/b2Jmc3BhcmFtPSZyZW1hcmtzPWludmFsaWQtYmFzZTY0"
    )
    proxy = _parse_ssr(config)
    assert proxy is not None
    assert proxy.details["params"]["remarks"] == "\x8a{Ú\x96'~m«\x1eë"


def test_parse_v2ray_json_with_invalid_json():
    """Test that _parse_v2ray_json handles invalid JSON."""
    config = (
        '{"outbound": {"protocol": "vmess", "settings": {"vnext": [{"address": "ju-tt.name", '
        '"port": 443, "users": [{"id": "03d011f0-38e8-4f99-9bf9-501d3c7e1f91"}]}]}}}'
    )
    assert _parse_v2ray_json(config) is not None

    config = (
        '{"outbound": {"protocol": "vmess", "settings": {"vnext": [{"address": "ju-tt.name", '
        '"port": 443, "users": [{"id": "03d011f0-38e8-4f99-9bf9-501d3c7e1f91"}]}'
    )
    assert _parse_v2ray_json(config) is None


def test_parse_v2ray_json_with_no_outbound():
    """Test that _parse_v2ray_json handles JSON with no outbound."""
    config = '{"inbound": {}}'
    assert _parse_v2ray_json(config) is None


def test_parse_v2ray_json_with_no_server_info():
    """Test that _parse_v2ray_json handles JSON with no server info."""
    config = '{"outbound": {"protocol": "vmess", "settings": {}}}'
    assert _parse_v2ray_json(config) is None


def test_parse_v2ray_json_with_no_address():
    """Test that _parse_v2ray_json handles JSON with no address."""
    config = (
        '{"outbound": {"protocol": "vmess", "settings": {"vnext": [{"port": 443, '
        '"users": [{"id": "03d011f0-38e8-4f99-9bf9-501d3c7e1f91"}]}]}}}'
    )
    assert _parse_v2ray_json(config) is None


def test_parse_v2ray_json_with_no_port():
    """Test that _parse_v2ray_json handles JSON with no port."""
    config = (
        '{"outbound": {"protocol": "vmess", "settings": {"vnext": [{"address": "ju-tt.name", '
        '"users": [{"id": "03d011f0-38e8-4f99-9bf9-501d3c7e1f91"}]}]}}}'
    )
    assert _parse_v2ray_json(config) is None


def test_parse_hysteria_with_invalid_port():
    """Test that _parse_hysteria handles invalid ports."""
    config = "hysteria://ju-tt.name:70000?protocol=udp&auth=123456#test"
    assert _parse_hysteria(config) is None


def test_parse_hysteria2_with_no_password():
    """Test that _parse_hysteria2 handles missing passwords."""
    config = "hysteria2://ju-tt.name:443#test"
    assert _parse_hysteria2(config) is None


def test_parse_tuic_with_invalid_port():
    """Test that _parse_tuic handles invalid ports."""
    config = (
        "tuic://03d011f0-38e8-4f99-9bf9-501d3c7e1f91:123456@ju-tt.name:70000"
        "?congestion_control=bbr#test"
    )
    assert _parse_tuic(config) is None
