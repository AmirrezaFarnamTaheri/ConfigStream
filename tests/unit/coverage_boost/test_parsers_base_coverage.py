from configstream.models import Proxy
from configstream.parsers.base import (extract_config_lines,
                                       is_plausible_proxy_config,
                                       normalize_proxy_details,
                                       safe_b64_decode, validate_b64_input)


def test_validate_b64_input_valid():
    assert validate_b64_input("SGVsbG8=") == "SGVsbG8="


def test_validate_b64_input_invalid_chars():
    # If noise ratio > 5%, returns None
    invalid = "SGVsbG8=" + "*" * 100
    assert validate_b64_input(invalid) is None


def test_validate_b64_input_empty():
    assert validate_b64_input("") is None


def test_safe_b64_decode_valid():
    assert safe_b64_decode("SGVsbG8=") == "Hello"


def test_safe_b64_decode_invalid():
    # Should return None if decode fails or validation fails
    # "invalid_b64" actually decodes to garbage because _, a-z, 0-9 are valid base64 chars.
    # Use characters not in base64 alphabet like !@#
    assert safe_b64_decode("!@#$%^&*()") is None


def test_is_plausible_proxy_config():
    # Needs long enough rest part (len > 3)
    assert is_plausible_proxy_config("vmess://abcdefg") is True
    assert (
        is_plausible_proxy_config("http://github.com/subs") is False
    )  # Blocked domain
    assert is_plausible_proxy_config("unknown://abcdefg") is True  # Checks syntax only


def test_extract_config_lines():
    # Valid lines must be plausible
    payload = "vmess://abcdefg\n# comment\nss://abcdefg"
    lines, stats = extract_config_lines(payload)
    assert len(lines) == 2
    assert "vmess://abcdefg" in lines
    assert "ss://abcdefg" in lines
    assert stats is not None


def test_normalize_proxy_details():
    proxy = Proxy(
        config="vmess://test",
        protocol="vmess",
        address="1.1.1.1",
        port=443,
        details={"host": "example.com"},
    )
    normalize_proxy_details(proxy)
    assert proxy.details["sni"] == "example.com"

    proxy2 = Proxy(
        config="vmess://test2",
        protocol="vmess",
        address="1.1.1.1",
        port=443,
        details={"serviceName": "/grpc"},
    )
    normalize_proxy_details(proxy2)
    assert proxy2.details["path"] == "/grpc"


def test_validate_b64_input_url_encoding(caplog):
    # Test auto-fix URL encoded
    # %3D is =
    encoded = "SGVsbG8%3D"
    decoded = validate_b64_input(encoded)
    assert decoded == "SGVsbG8="
