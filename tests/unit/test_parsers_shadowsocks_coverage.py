
import pytest
from src.configstream.parsers.shadowsocks import parse_ss, parse_ss2022
from src.configstream.models import Proxy
from unittest.mock import patch
import binascii

# --- parse_ss ---

def test_parse_ss_invalid_scheme():
    assert parse_ss("vmess://foo") is None

def test_parse_ss_sip002_basic():
    # ss://user:pass@1.2.3.4:8888
    # base64(user:pass@1.2.3.4:8888) -> dXNlcjpwYXNzQDEuMi4zLjQ6ODg4OA==
    config = "ss://dXNlcjpwYXNzQDEuMi4zLjQ6ODg4OA=="
    p = parse_ss(config)
    assert p.protocol == "shadowsocks"
    assert p.address == "1.2.3.4"
    assert p.port == 8888
    assert p.details["method"] == "user"
    assert p.details["password"] == "pass"

def test_parse_ss_sip002_bad_decode():
    # Not base64
    assert parse_ss("ss://!!!") is None
    # Decodes but no @
    # base64("hello") -> aGVsbG8=
    assert parse_ss("ss://aGVsbG8=") is None

def test_parse_ss_legacy_basic():
    # ss://method:password@hostname:port
    config = "ss://method:password@1.2.3.4:8888"
    p = parse_ss(config)
    assert p.address == "1.2.3.4"
    assert p.port == 8888
    assert p.details["method"] == "method"
    assert p.details["password"] == "password"

def test_parse_ss_legacy_b64_userinfo():
    # ss://base64(method:password)@hostname:port
    # method:password -> bWV0aG9kOnBhc3N3b3Jk
    config = "ss://bWV0aG9kOnBhc3N3b3Jk@1.2.3.4:8888"
    p = parse_ss(config)
    assert p.details["method"] == "method"
    assert p.details["password"] == "password"

def test_parse_ss_legacy_bad_userinfo_format():
    # No colon in userinfo
    # ss://nomethod@1.2.3.4:8888
    config = "ss://nomethod@1.2.3.4:8888"
    assert parse_ss(config) is None

def test_parse_ss_legacy_bad_hostinfo_format():
    # No colon in hostinfo
    config = "ss://m:p@no_port"
    assert parse_ss(config) is None

def test_parse_ss_invalid_port():
    config = "ss://m:p@1.2.3.4:abc"
    assert parse_ss(config) is None
    config = "ss://m:p@1.2.3.4:0"
    assert parse_ss(config) is None

def test_parse_ss_remarks_and_query():
    # ss://...@host:port#remark?plugin=obfs-local;obfs-host=google.com
    # remark needs to be url encoded?
    # Logic: remark_part = "remark?plugin=..."
    # remark_str, _, query_str = "remark", "?", "plugin=..."
    config = "ss://method:pass@1.2.3.4:8888#My%20Proxy?plugin=obfs"
    p = parse_ss(config)
    assert p.remarks == "My Proxy"
    assert p.details["plugin"] == "obfs"

def test_parse_ss_ipv6():
    config = "ss://method:pass@[2001:db8::1]:8888"
    p = parse_ss(config)
    assert p.address == "2001:db8::1"
    assert p.port == 8888

def test_parse_ss_exception():
    # Force exception inside
    with patch("src.configstream.parsers.shadowsocks.unquote") as mock_unquote:
        mock_unquote.side_effect = ValueError("Boom")
        assert parse_ss("ss://foo") is None

# --- parse_ss2022 ---

def test_parse_ss2022_invalid_scheme():
    assert parse_ss2022("ss://foo") is None

def test_parse_ss2022_valid():
    config = "ss2022://method:pass@1.2.3.4:8888"
    p = parse_ss2022(config)
    assert p is not None
    assert p.protocol == "ss2022"
    assert p.config == config
    assert p.address == "1.2.3.4"

def test_parse_ss2022_exception():
    # Underlying parse_ss fails?
    with patch("src.configstream.parsers.shadowsocks.parse_ss") as mock_parse:
        mock_parse.side_effect = Exception("Boom")
        assert parse_ss2022("ss2022://foo") is None
