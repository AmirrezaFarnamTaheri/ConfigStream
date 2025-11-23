
import pytest
from src.configstream.parsers.generic import (
    parse_generic_url_scheme,
    parse_naive,
    parse_v2ray_json,
)
from src.configstream.models import Proxy
from unittest.mock import patch, MagicMock

# --- parse_generic_url_scheme ---

def test_parse_generic_url_scheme_invalid_host():
    assert parse_generic_url_scheme("http://garbage:80") is None # filtered garbage
    assert parse_generic_url_scheme("http://garbage") is None
    assert parse_generic_url_scheme("http://inVALid") is None
    assert parse_generic_url_scheme("http://") is None
    assert parse_generic_url_scheme("http://?query") is None

def test_parse_generic_url_scheme_host_chars():
    # Only alnum, . - _ allowed (except [])
    assert parse_generic_url_scheme("http://bad$host.com") is None

def test_parse_generic_url_scheme_no_dot():
    # except localhost
    assert parse_generic_url_scheme("http://nodots") is None
    assert parse_generic_url_scheme("http://localhost") is not None

def test_parse_generic_url_scheme_invalid_port():
    assert parse_generic_url_scheme("http://example.com:65536") is None

def test_parse_generic_url_scheme_default_port():
    p = parse_generic_url_scheme("http://example.com")
    assert p.port == 80
    p = parse_generic_url_scheme("https://example.com")
    assert p.port == 443

    # Hit missing line 43: port = parsed.port or default_ports.get(parsed.scheme, 80)
    # Testing default port when scheme is unknown
    p = parse_generic_url_scheme("unknownscheme://example.com")
    assert p.port == 80

def test_parse_generic_url_scheme_exception():
    assert parse_generic_url_scheme("http://example.com:abc") is None

    # Mock to ensure we hit the exception block
    with patch("src.configstream.parsers.generic.urlparse") as mock_urlparse:
        mock_urlparse.side_effect = ValueError("Boom")
        assert parse_generic_url_scheme("http://foo") is None

# --- parse_naive ---

def test_parse_naive_missing_auth():
    assert parse_naive("naive+https://example.com") is None
    assert parse_naive("naive+https://user@example.com") is None
    assert parse_naive("naive+https://:pass@example.com") is None

def test_parse_naive_valid():
    p = parse_naive("naive+https://u:p@example.com")
    assert p.protocol == "naive"
    assert p.address == "example.com"
    assert p.port == 443
    assert p.uuid == "u"
    assert p.details["password"] == "p"

def test_parse_naive_exception():
    assert parse_naive("naive+https://example.com:abc") is None

    with patch("src.configstream.parsers.generic.urlparse") as mock_urlparse:
        mock_urlparse.side_effect = IndexError("Boom")
        assert parse_naive("naive+https://foo") is None

    # Force a validation error when creating Proxy to hit generic exception or debug log?
    # parse_naive catches ValueError, IndexError.
    # If Proxy() raises ValidationError (which is ValueError subclass in Pydantic V2? No, ValidationError)
    # Pydantic V2 ValidationError inherits from ValueError? No.
    # But if we pass something invalid to Proxy...
    # The try/except wraps the whole block.
    # Let's mock Proxy to raise ValueError
    with patch("src.configstream.parsers.generic.Proxy") as mock_proxy:
        mock_proxy.side_effect = ValueError("Invalid proxy")
        assert parse_naive("naive+https://u:p@example.com") is None

# --- parse_v2ray_json ---

def test_parse_v2ray_json_not_json():
    assert parse_v2ray_json("not json") is None
    assert parse_v2ray_json("{invalid json") is None

def test_parse_v2ray_json_no_outbound():
    assert parse_v2ray_json("{}") is None
    assert parse_v2ray_json('{"outbounds": []}') is None
    assert parse_v2ray_json('{"outbounds": "not-list"}') is None

    # Coverage for line 75: if not outbound:
    # Need to satisfy line 73: if not outbound and isinstance(outbounds, list) and outbounds:
    # but then NOT find outbound?
    # If outbounds is [{'protocol': 'v2ray'}] then outbound becomes that dict.
    # So to hit line 75's return None, we need:
    # 1. outbound is None (data.get("outbound") is None)
    # 2. outbounds logic fails to set outbound (e.g. empty list or not list)
    # 3. So outbound stays None.
    # This is covered by test_parse_v2ray_json_no_outbound('{"outbounds": []}')
    pass

def test_parse_v2ray_json_no_server_info():
    # Outbound exists but no vnext/servers
    json_conf = '{"outbound": {"protocol": "vmess", "settings": {}}}'
    assert parse_v2ray_json(json_conf) is None

    # vnext empty
    json_conf = '{"outbound": {"protocol": "vmess", "settings": {"vnext": []}}}'
    assert parse_v2ray_json(json_conf) is None

def test_parse_v2ray_json_missing_address_port():
    # vnext item missing address
    json_conf = '{"outbound": {"settings": {"vnext": [{"port": 80}]}}}'
    assert parse_v2ray_json(json_conf) is None

    # missing port
    json_conf = '{"outbound": {"settings": {"vnext": [{"address": "1.1.1.1"}]}}}'
    assert parse_v2ray_json(json_conf) is None

def test_parse_v2ray_json_invalid_port():
    # port is "abc"
    json_conf = '{"outbound": {"settings": {"vnext": [{"address": "1.1.1.1", "port": "abc"}]}}}'
    # This hits the try/except ValueError block at end
    assert parse_v2ray_json(json_conf) is None

def test_parse_v2ray_json_valid_outbounds_list():
    json_conf = """
    {
        "outbounds": [
            {
                "protocol": "vmess",
                "settings": {
                    "vnext": [
                        {
                            "address": "1.2.3.4",
                            "port": 10086,
                            "users": [{"id": "uuid-123"}]
                        }
                    ]
                },
                "tag": "test-tag"
            }
        ]
    }
    """
    p = parse_v2ray_json(json_conf)
    assert p is not None
    assert p.address == "1.2.3.4"
    assert p.port == 10086
    assert p.uuid == "uuid-123"
    assert p.remarks == "test-tag"

def test_parse_v2ray_json_servers_key():
    # Some configs might use 'servers' instead of 'vnext'
    json_conf = """
    {
        "outbound": {
            "settings": {
                "servers": [
                    {"ip": "8.8.8.8", "port": 53}
                ]
            }
        }
    }
    """
    p = parse_v2ray_json(json_conf)
    assert p.address == "8.8.8.8"
    assert p.port == 53
