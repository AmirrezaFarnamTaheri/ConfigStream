
import pytest
from src.configstream.parsers.ssr import parse_ssr
from src.configstream.models import Proxy
from unittest.mock import patch
import base64

def _encode_ssr(s):
    # urlsafe b64 encode without padding
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")

def test_parse_ssr_invalid_scheme():
    assert parse_ssr("ss://foo") is None

def test_parse_ssr_too_large():
    # payload > 4096
    payload = "a" * 4097
    assert parse_ssr(f"ssr://{payload}") is None

def test_parse_ssr_invalid_base64():
    assert parse_ssr("ssr://!!!") is None
    # safe_b64_decode returns the input if invalid, BUT _b64_normalize assumes string ops.
    # If safe_b64_decode returns the input "!!!", then split fails?
    # No, split works.
    # main, _, qs = "!!!".partition("/?") -> main="!!!", qs=""
    # main.split(":", 5) -> ["!!!"] -> len 1.
    # len != 6 -> return None.
    # So covered.

def test_parse_ssr_valid_basic():
    # server:port:protocol:method:obfs:password_base64_urlsafe
    # 1.2.3.4:8888:origin:aes-256-cfb:plain:password
    # password="password" -> cGFzc3dvcmQ
    raw = "1.2.3.4:8888:origin:aes-256-cfb:plain:cGFzc3dvcmQ"
    encoded = _encode_ssr(raw)
    config = f"ssr://{encoded}"
    p = parse_ssr(config)
    assert p.protocol == "ssr"
    assert p.address == "1.2.3.4"
    assert p.port == 8888
    assert p.details["protocol"] == "origin"
    assert p.details["cipher"] == "aes-256-cfb"
    assert p.details["obfs"] == "plain"
    # password is decoded
    assert p.details["password"] == "password"

def test_parse_ssr_with_qs():
    # .../?remarks=...&group=...
    # remarks="MyProxy" -> TXlQcm94eQ
    raw = "1.2.3.4:8888:origin:aes-256-cfb:plain:cGFzc3dvcmQ/?remarks=TXlQcm94eQ&group=Z3JvdXA"
    encoded = _encode_ssr(raw)
    config = f"ssr://{encoded}"
    p = parse_ssr(config)
    assert p.remarks == "MyProxy"
    assert p.details["params"]["group"] == "group"

def test_parse_ssr_invalid_parts_len():
    # Only 5 parts
    raw = "1.2.3.4:8888:origin:aes-256-cfb:plain"
    encoded = _encode_ssr(raw)
    config = f"ssr://{encoded}"
    assert parse_ssr(config) is None

def test_parse_ssr_invalid_host_len():
    # host > 255
    host = "a" * 256
    raw = f"{host}:8888:origin:aes-256-cfb:plain:pass"
    encoded = _encode_ssr(raw)
    config = f"ssr://{encoded}"
    assert parse_ssr(config) is None

def test_parse_ssr_invalid_port():
    raw = "1.2.3.4:abc:origin:aes-256-cfb:plain:pass"
    encoded = _encode_ssr(raw)
    config = f"ssr://{encoded}"
    assert parse_ssr(config) is None

    raw = "1.2.3.4:70000:origin:aes-256-cfb:plain:pass"
    encoded = _encode_ssr(raw)
    config = f"ssr://{encoded}"
    assert parse_ssr(config) is None

def test_parse_ssr_params_handling():
    # Test params decoding logic:
    # 1. Empty val
    # 2. Invalid b64 val
    # 3. Valid b64 val

    # query: empty=&bad=!!!&good=Z29vZA (good)
    qs_raw = "/?empty=&bad=!!!&good=Z29vZA"
    # Need to construct full payload
    raw_main = "1.2.3.4:8888:origin:aes-256-cfb:plain:cGFzc3dvcmQ"
    full = raw_main + qs_raw
    encoded = _encode_ssr(full)
    config = f"ssr://{encoded}"

    p = parse_ssr(config)
    params = p.details["params"]
    assert params["empty"] == ""
    assert params["bad"] == "!!!" # invalid b64 kept as is
    assert params["good"] == "good"

def test_parse_ssr_exception():
    with patch("src.configstream.parsers.ssr.safe_b64_decode") as mock_decode:
        mock_decode.side_effect = ValueError("Boom")
        # Trigger safe_b64_decode call at line 23
        assert parse_ssr("ssr://aaaa") is None
