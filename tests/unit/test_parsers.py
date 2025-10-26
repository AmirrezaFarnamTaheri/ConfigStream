from configstream.parsers import (
    _parse_vmess,
    _parse_vless,
    _parse_trojan,
    _parse_ss,
    _parse_ssr,
    _parse_generic_url_scheme,
    _parse_naive,
    _parse_v2ray_json,
    _parse_hysteria,
    _parse_hysteria2,
    _parse_tuic,
    _parse_wireguard,
    _parse_xray,
)
from configstream.core import parse_config


def test_parse_vmess():
    config = "vmess://ewogICJ2IjogIjIiLAogICJwcyI6ICJqdS10dC5uYW1lIiwKICAiYWRkIjogImp1LXR0Lm5hbWUiLAogICJwb3J0IjogIjQ0MyIsCiAgImlkIjogIjAzZDAxMWYwLTM4ZTgtNGY5OS05YmY5LTUwMWQzYzdlMWY5MSIsCiAgImFpZCI6ICIwIiwKICAibmV0IjogIndzIiwKICAidHlwZSI6ICJub25lIiwKICAiaG9zdCI6ICJ3d3cuZ29vZ2xlLmNvbSIsCiAgInBhdGgiOiAiL2FsaXRhIiwKICAidGxzIjogInRscyIKfQ=="
    proxy = _parse_vmess(config)
    assert proxy is not None
    assert proxy.protocol == "vmess"
    assert proxy.address == "ju-tt.name"


def test_parse_vless():
    config = "vless://03d011f0-38e8-4f99-9bf9-501d3c7e1f91@ju-tt.name:443?encryption=none&security=tls&type=ws&host=www.google.com&path=%2falita#ju-tt.name"
    proxy = _parse_vless(config)
    assert proxy is not None
    assert proxy.protocol == "vless"
    assert proxy.address == "ju-tt.name"


def test_parse_trojan():
    config = (
        "trojan://03d011f0-38e8-4f99-9bf9-501d3c7e1f91@ju-tt.name:443?sni=www.google.com#ju-tt.name"
    )
    proxy = _parse_trojan(config)
    assert proxy is not None
    assert proxy.protocol == "trojan"
    assert proxy.address == "ju-tt.name"


def test_parse_ss():
    config = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmRAanUtdHQuY29tOjQ0Mw==#ju-tt.name"
    proxy = _parse_ss(config)
    assert proxy is not None
    assert proxy.protocol == "shadowsocks"
    assert proxy.address == "ju-tt.com"


def test_parse_ssr():
    config = "ssr://anUtdHQuY29tOjQ0MzphdXRoX2FlczEyOF9tZDU6YWVzLTI1Ni1jZmI6dGxzMS4yX3RpY2tldF9hdXRoOlFYVjNZWEJwYnk1amJ5NWpiMjB2ZFc1a1lYQnBiV0Z6ZEdWeWMybHZiajB4T0RBd01EQXdNREF3TURBd01EQXdNQS8/b2Jmc3BhcmFtPSZwcm90b3BhcmFtPSZyZW1hcmtzPWRXNTBrWFIxYzJWd2N5NWtiMk5vWVhKcFkyVXVZMjl0Jmdyb3VwPVEyOVRiR2wwYVc5dWN5NXdibWM"
    proxy = _parse_ssr(config)
    assert proxy is not None
    assert proxy.protocol == "ssr"
    assert proxy.address == "ju-tt.com"


def test_parse_generic_url_scheme():
    config = "http://user:pass@example.com:8080#test"
    proxy = _parse_generic_url_scheme(config)
    assert proxy is not None
    assert proxy.protocol == "http"
    assert proxy.address == "example.com"
    assert proxy.port == 8080


def test_parse_naive():
    config = "naive+https://user:pass@example.com:443#test"
    proxy = _parse_naive(config)
    assert proxy is not None
    assert proxy.protocol == "naive"
    assert proxy.address == "example.com"


def test_parse_v2ray_json():
    config = '{"outbound": {"protocol": "vmess", "settings": {"vnext": [{"address": "ju-tt.name", "port": 443, "users": [{"id": "03d011f0-38e8-4f99-9bf9-501d3c7e1f91"}]}]}}}'
    proxy = _parse_v2ray_json(config)
    assert proxy is not None
    assert proxy.protocol == "v2ray"
    assert proxy.address == "ju-tt.name"


def test_parse_hysteria():
    config = "hysteria://ju-tt.name:443?protocol=udp&auth=123456#test"
    proxy = _parse_hysteria(config)
    assert proxy is not None
    assert proxy.protocol == "hysteria"


def test_parse_hysteria2():
    config = "hysteria2://123456@ju-tt.name:443#test"
    proxy = _parse_hysteria2(config)
    assert proxy is not None
    assert proxy.protocol == "hysteria2"


def test_parse_tuic():
    config = "tuic://03d011f0-38e8-4f99-9bf9-501d3c7e1f91:123456@ju-tt.name:443?congestion_control=bbr#test"
    proxy = _parse_tuic(config)
    assert proxy is not None
    assert proxy.protocol == "tuic"


def test_parse_wireguard():
    config = "wg://123456@1.1.1.1:51820?private_key=key&peer_public_key=abcdefg#test"
    proxy = _parse_wireguard(config)
    assert proxy is not None
    assert proxy.protocol == "wireguard"


def test_parse_xray():
    config = "xray://123456@1.1.1.1:443?security=tls#test"
    proxy = _parse_xray(config)
    assert proxy is not None
    assert proxy.protocol == "xray"


def test_parse_invalid():
    proxy = parse_config("invalid://config")
    assert proxy is None


def test_parse_empty():
    assert parse_config("") is None
    assert parse_config(None) is None


def test_parse_invalid_vmess():
    # Invalid base64
    config = "vmess://invalid-base64"
    assert parse_config(config) is None
    # Missing required fields
    config = (
        "vmess://ewogICJ2IjogIjIiLAogICJwcyI6ICJqdS10dC5uYW1lIiwKICAiYWRkIjogImp1LXR0Lm5hbWUiCn0="
    )
    assert parse_config(config) is None


def test_parse_invalid_vless():
    # Invalid port
    config = "vless://03d011f0-38e8-4f99-9bf9-501d3c7e1f91@ju-tt.name:70000?encryption=none&security=tls&type=ws&host=www.google.com&path=%2falita#ju-tt.name"
    assert parse_config(config) is None
    # No hostname
    config = "vless://03d011f0-38e8-4f99-9bf9-501d3c7e1f91@:443?encryption=none&security=tls&type=ws&host=www.google.com&path=%2falita#ju-tt.name"
    assert parse_config(config) is None


def test_parse_invalid_ss():
    # Invalid base64
    config = "ss://invalid-base64@ju-tt.name:443#ju-tt.name"
    assert parse_config(config) is None
    # Malformed
    config = "ss://YWVzLTI1Ni1nY206M2QwMTFmMC0zOGU4LTRmOTktOWJmOS01MDFkM2M3ZTFmOTE@ju-tt.name"
    assert parse_config(config) is None


def test_parse_invalid_ssr():
    # Invalid base64
    config = "ssr://invalid-base64"
    assert parse_config(config) is None
    # Malformed
    config = (
        "ssr://anUtdHQuY29tOjQ0MzphdXRoX2FlczEyOF9tZDU6YWVzLTI1Ni1jZmI6dGxzMS4yX3RpY2tldF9hdXRo"
    )
    assert parse_config(config) is None


def test_parse_invalid_trojan():
    # Invalid port
    config = "trojan://03d011f0-38e8-4f99-9bf9-501d3c7e1f91@ju-tt.name:70000?sni=www.google.com#ju-tt.name"
    assert parse_config(config) is None
    # No hostname
    config = "trojan://03d011f0-38e8-4f99-9bf9-501d3c7e1f91@:443?sni=www.google.com#ju-tt.name"
    assert parse_config(config) is None


def test_parse_invalid_v2ray_json():
    # Invalid JSON
    config = '{"outbound": {"protocol": "vmess", "settings": {"vnext": [{"address": "ju-tt.name", "port": 443, "users": [{"id": "03d011f0-38e8-4f99-9bf9-501d3c7e1f91"}]}]}}'
    assert parse_config(config) is None
    # No outbound
    config = '{"ps": "ju-tt.name"}'
    assert parse_config(config) is None


from configstream.parsers import _validate_b64_input, _safe_b64_decode


def test_validate_b64_input():
    # Valid
    assert _validate_b64_input("SGVsbG8gV29ybGQ=") == "SGVsbG8gV29ybGQ="
    # Invalid
    assert _validate_b64_input("SGVsbG8gV29ybGQ") == "SGVsbG8gV29ybGQ="
    # Empty
    assert _validate_b64_input("") is None


def test_safe_b64_decode():
    # Valid
    assert _safe_b64_decode("SGVsbG8gV29ybGQ=") == "Hello World"
    # Invalid
    assert _safe_b64_decode("SGVsbG8gV29ybGQ") == "Hello World"
    # Empty
    assert _safe_b64_decode("") == ""


def test_parse_vmess_edge_cases():
    """Test VMess parsing edge cases."""
    from configstream.parsers import _parse_vmess

    # Test with minimal config
    result = _parse_vmess("vmess://invalid")
    assert result is None

    # Test with empty string
    result = _parse_vmess("")
    assert result is None


def test_parse_vless_edge_cases():
    """Test VLESS parsing edge cases."""
    from configstream.parsers import _parse_vless

    # Test with invalid format
    result = _parse_vless("vless://")
    assert result is None


def test_parse_trojan_edge_cases():
    """Test Trojan parsing edge cases."""
    from configstream.parsers import _parse_trojan

    # Test with minimal config
    result = _parse_trojan("trojan://")
    assert result is None


def test_parse_ss_edge_cases():
    """Test Shadowsocks parsing edge cases."""
    from configstream.parsers import _parse_ss

    # Test with invalid base64
    result = _parse_ss("ss://notbase64!")
    assert result is None
