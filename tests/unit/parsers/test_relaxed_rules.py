import json
import pytest
from configstream.parsers.shadowsocks import parse_ss
from configstream.parsers.others import parse_wireguard
from configstream.parsers.vmess import parse_vmess
from configstream.parsers.extraction import extract_config_lines
from configstream.models import Proxy

def test_shadowsocks_short_method():
    # 'rc4' is 3 chars, previously allowed (>=3).
    # 'd' is 1 char (blocked <2). 'rc' is 2 chars (allowed >=2).
    # Let's test a 2-char method 'rc' (hypothetical legacy)
    config = "ss://cmM6cGFzc3dvcmRAMS4xLjEuMTo0NDM=" # rc:password@1.1.1.1:443
    proxy = parse_ss(config)
    assert proxy is not None
    assert proxy.details["method"] == "rc"

def test_wireguard_urlencoded_key():
    # Key with + encoded as %2B
    # Original: aGVsbG93b3JsZH3d3d3d3d3d3d3d3d3d3d3d3d3d3d= (44 chars)
    # Encoded: aGVsbG93b3JsZH3d3d3d3d3d3d3d3d3d3d3d3d3d3d%3D
    # Or a key with +: "abcd+efg..." -> "abcd%2Befg..."

    # Valid WG private key (dummy): 44 chars Base64
    # "yAnz5OGQ/i+q4g5+8/x/4w==" -> length 24? No.
    # 32 bytes = 44 base64 chars.
    valid_key = "a" * 43 + "="
    encoded_key = "a" * 43 + "%3D" # Encode the =

    config = f"wireguard://user:pass@1.1.1.1:51820?private_key={encoded_key}&peer_public_key={valid_key}"
    proxy = parse_wireguard(config)
    assert proxy is not None
    assert proxy.details["private_key"] == valid_key

def test_vmess_respects_aid():
    # Construct a valid VMess config with aid=64
    import base64
    vmess_payload = {
        "v": "2",
        "ps": "test-vmess",
        "add": "1.1.1.1",
        "port": 443,
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "aid": 64,  # Legacy
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": "example.com",
        "path": "/",
        "tls": "tls"
    }
    json_str = json.dumps(vmess_payload)
    b64_str = base64.b64encode(json_str.encode()).decode()
    config = f"vmess://{b64_str}"

    proxy = parse_vmess(config)
    assert proxy is not None
    assert proxy.protocol == "vmess"
    # The parser should now respect aid=64
    assert proxy.details["aid"] == 64

def test_vmess_defaults_to_zero_aid():
    # Construct a valid VMess config with NO aid
    import base64
    vmess_payload = {
        "v": "2",
        "ps": "test-vmess",
        "add": "1.1.1.1",
        "port": 443,
        "id": "550e8400-e29b-41d4-a716-446655440000",
        # missing aid
        "net": "tcp"
    }
    json_str = json.dumps(vmess_payload)
    b64_str = base64.b64encode(json_str.encode()).decode()
    config = f"vmess://{b64_str}"

    proxy = parse_vmess(config)
    assert proxy is not None
    assert proxy.details["aid"] == 0

def test_extract_ipv6_bare():
    # Test extracting bare [IPv6]:Port
    payload = """
    1.2.3.4:80
    [2001:db8::1]:443
    garbage
    """
    lines, drops = extract_config_lines(payload)

    assert len(lines) == 2
    assert "http://1.2.3.4:80" in lines
    assert "http://[2001:db8::1]:443" in lines
    assert "missing_protocol_separator" in drops or "implausible_format" in drops
