"""Tests for security rules."""

import pytest
from configstream.security.rules import (
    validate_port,
    validate_address,
    validate_protocol,
    validate_config_string,
    SECURITY_CATEGORIES,
    MAX_PORT,
)
from configstream.config import AppSettings
from unittest.mock import patch, MagicMock


def test_validate_port():
    assert validate_port(80) is None
    assert validate_port(443) is None

    # Boundary checks
    assert validate_port(0) is not None
    assert validate_port(65536) is not None

    # Dangerous ports
    assert validate_port(22) is not None  # SSH
    assert validate_port(23) is not None  # Telnet


def test_validate_address():
    allowlist = frozenset({"allowed.com"})

    # Valid cases
    assert validate_address("google.com", allowlist) == {}
    assert validate_address("1.1.1.1", allowlist) == {}
    assert validate_address("allowed.com", allowlist) == {}
    assert validate_address("test.test", allowlist) == {}  # .test TLD

    # Mock SUSPICIOUS_DOMAINS to test that logic specifically
    with patch(
        "configstream.security.rules.SUSPICIOUS_DOMAINS", ["suspicious.com"]
    ):
        issues = validate_address("suspicious.com", allowlist)
        assert SECURITY_CATEGORIES["ADDRESS_SUSPICIOUS"] in issues

        issues = validate_address("sub.suspicious.com", allowlist)
        assert SECURITY_CATEGORIES["ADDRESS_SUSPICIOUS"] in issues

    # Empty
    issues = validate_address("", allowlist)
    assert SECURITY_CATEGORIES["ADDRESS_SUSPICIOUS"] in issues

    # Hex/Octal
    issues = validate_address("0x7f000001", allowlist)
    assert SECURITY_CATEGORIES["ADDRESS_SUSPICIOUS"] in issues

    issues = validate_address("0127.0.0.1", allowlist)
    assert SECURITY_CATEGORIES["ADDRESS_SUSPICIOUS"] in issues

    # Private IPs
    # Mock AppSettings to ensure ALLOW_PRIVATE_IPS is False
    # Also mock SUSPICIOUS_DOMAINS to be empty so we fall through to private IP check
    with (
        patch("configstream.security.rules._APP_SETTINGS_CACHE") as mock_settings,
        patch("configstream.security.rules.SUSPICIOUS_DOMAINS", []),
    ):
        mock_settings.ALLOW_PRIVATE_IPS = False

        issues = validate_address("127.0.0.1", allowlist)
        assert SECURITY_CATEGORIES["ADDRESS_PRIVATE"] in issues

        issues = validate_address("192.168.1.1", allowlist)
        assert SECURITY_CATEGORIES["ADDRESS_PRIVATE"] in issues

        issues = validate_address("10.0.0.1", allowlist)
        assert SECURITY_CATEGORIES["ADDRESS_PRIVATE"] in issues

        issues = validate_address("localhost", allowlist)
        assert SECURITY_CATEGORIES["ADDRESS_PRIVATE"] in issues

        # 172.16 (Private)
        issues = validate_address("172.16.0.1", allowlist)
        assert SECURITY_CATEGORIES["ADDRESS_PRIVATE"] in issues

    # Private IPs allowed
    with patch("configstream.security.rules._APP_SETTINGS_CACHE") as mock_settings:
        mock_settings.ALLOW_PRIVATE_IPS = True

        # We need to ensure it's NOT in SUSPICIOUS_DOMAINS for this test
        # because SUSPICIOUS_DOMAINS check happens BEFORE private IP check
        with patch("configstream.security.rules.SUSPICIOUS_DOMAINS", []):
            issues = validate_address("127.0.0.1", allowlist)
            assert issues == {}


def test_validate_protocol():
    assert validate_protocol("ss") is None
    assert validate_protocol("vmess") is None
    assert validate_protocol("unknown") is not None


def test_validate_config_string():
    # Valid
    assert validate_config_string("valid config") == {}

    # Empty
    issues = validate_config_string("")
    assert SECURITY_CATEGORIES["CONFIG_TOO_LONG"] in issues

    # Null byte
    issues = validate_config_string("config\x00malicious")
    assert SECURITY_CATEGORIES["CONFIG_NULL_BYTE"] in issues

    # Too long
    long_config = "a" * 10001
    with patch("configstream.security.rules.MAX_CONFIG_LINE_LENGTH", 10000):
        issues = validate_config_string(long_config)
        assert SECURITY_CATEGORIES["CONFIG_TOO_LONG"] in issues
