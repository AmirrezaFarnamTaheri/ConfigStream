
import pytest
from unittest.mock import MagicMock, patch
from src.configstream.parsers.base import (
    validate_b64_input,
    safe_b64_decode,
    is_plausible_proxy_config,
    extract_config_lines,
    normalize_proxy_details,
)
from src.configstream.constants import (
    MAX_B64_INPUT_SIZE,
    MAX_B64_OUTPUT_SIZE,
    MAX_CONFIG_LINE_LENGTH,
    MAX_LINES_PER_SOURCE,
)
from src.configstream.models import Proxy
import binascii

# --- validate_b64_input ---

def test_validate_b64_input_invalid_type():
    assert validate_b64_input(123) is None

def test_validate_b64_input_empty():
    assert validate_b64_input("   ") is None

def test_validate_b64_input_too_large():
    large_input = "A" * (MAX_B64_INPUT_SIZE + 1)
    assert validate_b64_input(large_input) is None

def test_validate_b64_input_invalid_chars():
    assert validate_b64_input("abc$") is None

def test_validate_b64_input_padding():
    # 'A' needs padding to be valid b64?
    # Actually 'A' decodes to 6 bits, usually needs 4 chars.
    # 'Any' -> 'Any=' to be multiple of 4.
    # validate_b64_input adds padding if needed.
    # 'QQ' (16 bits?) -> 'QQ=='
    res = validate_b64_input("QQ")
    assert res == "QQ=="

# --- safe_b64_decode ---

def test_safe_b64_decode_invalid_input():
    # validate_b64_input returns None for invalid chars
    assert safe_b64_decode("abc$") == "abc$"

def test_safe_b64_decode_too_large_output():
    with patch("base64.b64decode") as mock_decode:
        mock_decode.return_value = b"A" * (MAX_B64_OUTPUT_SIZE + 1)
        res = safe_b64_decode("AAAA")
        assert res == "AAAA"

def test_safe_b64_decode_memory_error():
    with patch("base64.b64decode") as mock_decode:
        mock_decode.side_effect = MemoryError("OOM")
        res = safe_b64_decode("AAAA")
        assert res == "AAAA"

def test_safe_b64_decode_binascii_error():
    with patch("base64.b64decode") as mock_decode:
        mock_decode.side_effect = binascii.Error("Bad padding")
        res = safe_b64_decode("AAAA")
        assert res == "AAAA"

def test_safe_b64_decode_exception():
    with patch("base64.b64decode") as mock_decode:
        mock_decode.side_effect = Exception("Boom")
        res = safe_b64_decode("AAAA")
        assert res == "AAAA"

def test_safe_b64_decode_latin1_fallback():
    invalid_utf8 = b'\xff\xfe'
    with patch("base64.b64decode") as mock_decode:
        mock_decode.return_value = invalid_utf8
        res = safe_b64_decode("AAAA")
        assert res == invalid_utf8.decode("latin-1")

def test_safe_b64_decode_success():
    # "SGVsbG8=" is "Hello"
    assert safe_b64_decode("SGVsbG8=") == "Hello"

# --- is_plausible_proxy_config ---

def test_is_plausible_proxy_config_openvpn():
    assert is_plausible_proxy_config("-----BEGIN CERTIFICATE-----") is True
    assert is_plausible_proxy_config("client\ndev tun\n") is True

def test_is_plausible_proxy_config_no_scheme():
    assert is_plausible_proxy_config("just text") is False

def test_is_plausible_proxy_config_short_rest():
    assert is_plausible_proxy_config("ss://") is False # rest is empty
    assert is_plausible_proxy_config("ss://a") is False # rest < 4

def test_is_plausible_proxy_config_long_protocol():
    proto = "a" * 21
    assert is_plausible_proxy_config(f"{proto}://abcd") is False

def test_is_plausible_proxy_config_too_many_special_chars():
    garbage = "@#$%^&*()_+{}|:<>?" * 10
    config = f"ss://{garbage}"
    assert is_plausible_proxy_config(config) is False

def test_is_plausible_proxy_config_valid():
    assert is_plausible_proxy_config("ss://valid-config-here") is True

# --- extract_config_lines ---

def test_extract_config_lines_invalid_payload():
    assert extract_config_lines(None) == []
    assert extract_config_lines("   ") == []

def test_extract_config_lines_openvpn_valid():
    payload = "client\ndev tun\nremote 1.1.1.1"
    assert extract_config_lines(payload) == [payload]

def test_extract_config_lines_openvpn_too_large():
    # Payload large -> falls back to line splitting.
    # Lines don't look like proxies -> empty result
    payload = "client\ndev tun\n" + "A" * MAX_B64_OUTPUT_SIZE
    lines = extract_config_lines(payload)
    assert lines == []

def test_extract_config_lines_truncation():
    # Use valid config strings
    valid_line = "ss://valid-proxy-config"
    lines = [valid_line] * (MAX_LINES_PER_SOURCE + 10)
    payload = "\n".join(lines)
    extracted = extract_config_lines(payload, max_lines=MAX_LINES_PER_SOURCE)
    assert len(extracted) == MAX_LINES_PER_SOURCE
    assert extracted[0] == valid_line

def test_extract_config_lines_filtering():
    payload = """
    # Comment
    ss://valid-proxy-1
    invalid://scheme
    too-short://a
    ss://
    """
    extracted = extract_config_lines(payload)
    assert len(extracted) == 1
    assert extracted[0] == "ss://valid-proxy-1"

def test_extract_config_lines_long_line():
    long_line = "ss://" + "a" * (MAX_CONFIG_LINE_LENGTH + 1)
    extracted = extract_config_lines(long_line)
    assert len(extracted) == 0

# --- normalize_proxy_details ---

def _make_proxy(details=None):
    return Proxy(
        config="ss://test",
        protocol="shadowsocks",
        address="1.2.3.4",
        port=80,
        details=details or {}
    )

def test_normalize_proxy_details_empty():
    p = _make_proxy()
    normalize_proxy_details(p)
    assert p.details == {}

def test_normalize_proxy_details_sni_precedence():
    p = _make_proxy({
        "sni": "sni.com",
        "peer": "peer.com",
        "host": "host.com"
    })
    normalize_proxy_details(p)
    assert p.details["sni"] == "sni.com"

    p = _make_proxy({
        "peer": "peer.com",
        "host": "host.com"
    })
    normalize_proxy_details(p)
    assert p.details["sni"] == "peer.com"

def test_normalize_proxy_details_vmess_headers():
    p = Proxy(
        config="vmess://test",
        protocol="vmess",
        address="1.2.3.4",
        port=80,
        details={
            "headers": {"Host": "example.com"},
            "host": "bad.com"
        }
    )
    normalize_proxy_details(p)
    assert p.details["sni"] == "example.com"

def test_normalize_proxy_details_shadowsocks_plugin():
    p = Proxy(
        config="ss://test",
        protocol="shadowsocks",
        address="1.2.3.4",
        port=80,
        details={
            "plugin": "obfs-local;obfs-host=google.com;obfs-uri=/foo"
        }
    )
    normalize_proxy_details(p)
    assert p.details["sni"] == "google.com"
    assert p.details["path"] == "/foo"

def test_normalize_proxy_details_path_precedence():
    p = _make_proxy({
        "path": "/path",
        "serviceName": "/service"
    })
    normalize_proxy_details(p)
    assert p.details["path"] == "/path"

    p = _make_proxy({
        "serviceName": "/service"
    })
    normalize_proxy_details(p)
    assert p.details["path"] == "/service"

def test_normalize_proxy_details_alpn_list():
    p = _make_proxy({
        "alpn": ["h2", "http/1.1"]
    })
    normalize_proxy_details(p)
    assert p.details["alpn"] == ["h2", "http/1.1"]

def test_normalize_proxy_details_alpn_str():
    p = _make_proxy({
        "alpn": "h2, http/1.1"
    })
    normalize_proxy_details(p)
    assert p.details["alpn"] == ["h2", "http/1.1"]
