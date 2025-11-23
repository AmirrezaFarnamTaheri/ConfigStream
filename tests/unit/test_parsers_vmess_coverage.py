
import pytest
import base64
import json
from src.configstream.parsers.vmess import parse_vmess
from src.configstream.models import Proxy
from src.configstream.constants import MAX_CONFIG_LINE_LENGTH
from unittest.mock import patch

def _encode_vmess(data):
    return base64.b64encode(json.dumps(data).encode()).decode()

def test_parse_vmess_valid():
    data = {
        "add": "1.1.1.1",
        "port": 443,
        "id": "uuid",
        "ps": "MyVMess",
        "net": "ws",
        "host": "google.com"
    }
    config = f"vmess://{_encode_vmess(data)}"
    p = parse_vmess(config)
    assert p.protocol == "vmess"
    assert p.address == "1.1.1.1"
    assert p.port == 443
    assert p.uuid == "uuid"
    assert p.remarks == "MyVMess"
    assert p.details["net"] == "ws"

def test_parse_vmess_invalid_scheme():
    assert parse_vmess("ss://...") is None

def test_parse_vmess_too_long_input():
    # > 10000 chars
    data = "a" * 10001
    assert parse_vmess(f"vmess://{data}") is None

def test_parse_vmess_too_large_decoded():
    # > MAX_CONFIG_LINE_LENGTH
    # Need to construct base64 that fits in input limit but decodes to large?
    # Base64 is 4/3 size. 10000 input -> 7500 output.
    # If MAX_CONFIG_LINE_LENGTH < 7500, we can trigger it.
    # Assuming MAX_CONFIG_LINE_LENGTH is small enough?
    # Let's check constant.
    # If MAX_CONFIG_LINE_LENGTH is huge (e.g. 1MB), we can't trigger line 24 via line 17 check.
    # But if line 17 passes (10000 limit), decoded is at most ~7500.
    # So if MAX_CONFIG_LINE_LENGTH > 7500, lines 24-25 are dead code unless we mock?
    # Let's mock MAX_CONFIG_LINE_LENGTH or force check.
    with patch("src.configstream.parsers.vmess.MAX_CONFIG_LINE_LENGTH", 10):
        data = {"add": "1.1.1.1", "port": 443, "id": "u"} # this is > 10 chars
        config = f"vmess://{_encode_vmess(data)}"
        assert parse_vmess(config) is None

def test_parse_vmess_missing_fields():
    # Missing 'add'
    data = {"port": 443, "id": "u"}
    config = f"vmess://{_encode_vmess(data)}"
    assert parse_vmess(config) is None

def test_parse_vmess_invalid_port():
    data = {"add": "1.1.1.1", "port": "abc", "id": "u"}
    # int() raises ValueError -> caught
    config = f"vmess://{_encode_vmess(data)}"
    assert parse_vmess(config) is None

    data = {"add": "1.1.1.1", "port": 70000, "id": "u"}
    config = f"vmess://{_encode_vmess(data)}"
    assert parse_vmess(config) is None

def test_parse_vmess_invalid_address():
    # Empty
    data = {"add": "", "port": 443, "id": "u"}
    config = f"vmess://{_encode_vmess(data)}"
    assert parse_vmess(config) is None

    # Too long
    data = {"add": "a"*256, "port": 443, "id": "u"}
    config = f"vmess://{_encode_vmess(data)}"
    assert parse_vmess(config) is None

def test_parse_vmess_invalid_uuid():
    # Empty
    data = {"add": "1.1.1.1", "port": 443, "id": ""}
    config = f"vmess://{_encode_vmess(data)}"
    assert parse_vmess(config) is None

    # Too long
    data = {"add": "1.1.1.1", "port": 443, "id": "a"*101}
    config = f"vmess://{_encode_vmess(data)}"
    assert parse_vmess(config) is None

def test_parse_vmess_exception():
    # Invalid base64
    assert parse_vmess("vmess://!!!") is None
