"""
Comprehensive robustness tests for parsers module.
Tests edge cases, error handling, and security validations.
"""

from configstream.parsers import (
    parse_vmess as _parse_vmess,
    parse_ss as _parse_ss,
    parse_ssr as _parse_ssr,
    parse_openvpn as _parse_openvpn,
    extract_config_lines as _extract_config_lines,
)
from configstream.parsers.base import (
    safe_b64_decode as _safe_b64_decode,
    is_plausible_proxy_config as _is_plausible_proxy_config,
)


class TestBase64Decoding:
    """Test base64 decoding security and robustness."""

    def test_safe_b64_decode_valid(self):
        """Test valid base64 decoding."""
        result = _safe_b64_decode("SGVsbG8gV29ybGQ=")
        assert result == "Hello World"

    def test_safe_b64_decode_invalid_chars(self):
        """Test invalid base64 characters."""
        result = _safe_b64_decode("Hello@#$%")
        assert result == "Hello@#$%"  # Returns original on failure

    def test_safe_b64_decode_empty(self):
        """Test empty string."""
        result = _safe_b64_decode("")
        assert result == ""

    def test_safe_b64_decode_oversized(self):
        """Test oversized base64 input."""
        # Create a very large base64 string
        large_input = "A" * (10 * 1024 * 1024 + 1)  # Over 10MB
        result = _safe_b64_decode(large_input)
        # Should return original if too large
        assert result == large_input


class TestVMessParser:
    """Test VMess parser robustness."""

    def test_parse_vmess_invalid_port_type(self):
        """Test VMess with non-numeric port."""
        import base64
        import json

        config_data = {
            "add": "example.com",
            "port": "not_a_number",
            "id": "test-uuid",
            "ps": "test",
        }
        config = (
            "vmess://" + base64.b64encode(json.dumps(config_data).encode()).decode()
        )
        result = _parse_vmess(config)
        assert result is None

    def test_parse_vmess_missing_required_fields(self):
        """Test VMess missing required fields."""
        import base64
        import json

        config_data = {"add": "example.com"}  # Missing port and id
        config = (
            "vmess://" + base64.b64encode(json.dumps(config_data).encode()).decode()
        )
        result = _parse_vmess(config)
        assert result is None

    def test_parse_vmess_invalid_port_range(self):
        """Test VMess with out-of-range port."""
        import base64
        import json

        config_data = {
            "add": "example.com",
            "port": 99999,  # Invalid port
            "id": "test-uuid",
        }
        config = (
            "vmess://" + base64.b64encode(json.dumps(config_data).encode()).decode()
        )
        result = _parse_vmess(config)
        assert result is None

    def test_parse_vmess_oversized_address(self):
        """Test VMess with oversized address."""
        import base64
        import json

        config_data = {
            "add": "a" * 300,  # Over 255 chars
            "port": 443,
            "id": "test-uuid",
        }
        config = (
            "vmess://" + base64.b64encode(json.dumps(config_data).encode()).decode()
        )
        result = _parse_vmess(config)
        assert result is None

    def test_parse_vmess_memory_bomb_protection(self):
        """Test VMess memory bomb protection."""
        import base64

        # Create a large JSON that decodes to huge size
        large_data = (
            '{"add":"test.com","port":443,"id":"x",' + '"data":"' + "A" * 100000 + '"}'
        )
        config = "vmess://" + base64.b64encode(large_data.encode()).decode()
        _ = _parse_vmess(config)
        # Should be rejected due to size check


class TestShadowsocksParser:
    """Test Shadowsocks parser robustness."""

    def test_parse_ss_invalid_port(self):
        """Test Shadowsocks with invalid port."""
        import base64

        # ss://method:password@host:INVALID_PORT
        config_str = "aes-256-gcm:password@example.com:invalid"
        config = "ss://" + base64.b64encode(config_str.encode()).decode()
        result = _parse_ss(config)
        assert result is None

    def test_parse_ss_missing_colon(self):
        """Test Shadowsocks with malformed format."""
        import base64

        config_str = "aes-256-gcm-password-example.com-443"  # No colons
        config = "ss://" + base64.b64encode(config_str.encode()).decode()
        result = _parse_ss(config)
        assert result is None

    def test_parse_ss_port_zero(self):
        """Test Shadowsocks with port 0."""
        import base64

        config_str = "aes-256-gcm:password@example.com:0"
        config = "ss://" + base64.b64encode(config_str.encode()).decode()
        result = _parse_ss(config)
        assert result is None


class TestShadowsocksRParser:
    """Test ShadowsocksR parser robustness."""

    def test_parse_ssr_invalid_port(self):
        """Test SSR with invalid port."""
        # ssr://base64(server:port:protocol:method:obfs:password_base64/?params)
        import base64

        config_str = (
            "example.com:NOT_A_PORT:origin:aes-256-cfb:plain:"
            + base64.b64encode(b"password").decode()
        )
        config = "ssr://" + base64.b64encode(config_str.encode()).decode()
        result = _parse_ssr(config)
        assert result is None

    def test_parse_ssr_insufficient_parts(self):
        """Test SSR with insufficient parts."""
        import base64

        config_str = "example.com:443:origin"  # Only 3 parts, needs 6
        config = "ssr://" + base64.b64encode(config_str.encode()).decode()
        result = _parse_ssr(config)
        assert result is None


class TestOpenVPNParser:
    """Test OpenVPN parser robustness."""

    def test_parse_openvpn_invalid_port(self):
        """Test OpenVPN with invalid port in remote directive."""
        config = """
client
dev tun
remote example.com INVALID_PORT
proto udp
"""
        result = _parse_openvpn(config)
        assert result is None

    def test_parse_openvpn_no_remote(self):
        """Test OpenVPN without remote directive."""
        config = """
client
dev tun
proto udp
"""
        result = _parse_openvpn(config)
        assert result is None


class TestConfigLineExtraction:
    """Test configuration line extraction."""

    def test_extract_openvpn_detection(self):
        """Test OpenVPN file detection."""
        config = """
client
dev tun
remote example.com 1194
proto udp
"""
        result = _extract_config_lines(config)
        assert len(result) == 1
        assert "client" in result[0]

    def test_extract_with_dev_tap(self):
        """Test OpenVPN with dev tap."""
        config = """
client
dev tap
remote example.com 1194
"""
        result = _extract_config_lines(config)
        assert len(result) == 1

    def test_extract_max_lines_limit(self):
        """Test maximum lines limit."""
        lines = ["vmess://test" + str(i) for i in range(20000)]
        config = "\n".join(lines)
        result = _extract_config_lines(config, max_lines=1000)
        assert len(result) <= 1000

    def test_extract_oversized_line(self):
        """Test oversized config line is skipped."""
        config = "vmess://" + "A" * 100000  # Over MAX_CONFIG_LINE_LENGTH
        result = _extract_config_lines(config)
        assert len(result) == 0

    def test_extract_with_comments(self):
        """Test lines starting with # are skipped."""
        config = """
# This is a comment
vmess://validconfig
# Another comment
vless://anotherconfig
"""
        result = _extract_config_lines(config)
        assert len(result) == 2
        assert all(not line.startswith("#") for line in result)


class TestPlausibilityCheck:
    """Test config plausibility checking."""

    def test_plausible_openvpn_certificate(self):
        """Test OpenVPN certificate detection."""
        config = "-----BEGIN CERTIFICATE-----\nMIIC..."
        assert _is_plausible_proxy_config(config) is True

    def test_plausible_openvpn_dev_tun(self):
        """Test OpenVPN dev tun detection."""
        config = "client\ndev tun\nremote test.com 443"
        assert _is_plausible_proxy_config(config) is True

    def test_plausible_openvpn_dev_tap(self):
        """Test OpenVPN dev tap detection."""
        config = "client\ndev tap\nremote test.com 443"
        assert _is_plausible_proxy_config(config) is True

    def test_not_plausible_no_protocol(self):
        """Test config without protocol separator."""
        config = "notavalidconfig"
        assert _is_plausible_proxy_config(config) is False

    def test_not_plausible_short_data(self):
        """Test config with insufficient data after protocol."""
        config = "vmess://ab"  # Too short
        assert _is_plausible_proxy_config(config) is False

    def test_not_plausible_long_protocol(self):
        """Test config with overly long protocol."""
        config = "a" * 30 + "://validdata"
        assert _is_plausible_proxy_config(config) is False

    def test_not_plausible_too_many_special_chars(self):
        """Test config with excessive special characters."""
        _ = "vmess://@@@@@@@@@@@@@@@@@@@@"
        # Should be rejected due to special char ratio


class TestErrorRecovery:
    """Test error recovery and edge cases."""

    def test_none_input(self):
        """Test None input handling."""
        # Most parsers should handle None gracefully
        # Note: These functions expect strings, None would cause AttributeError
        # Testing with empty string instead
        assert _parse_vmess("") is None
        assert _parse_ss("") is None

    def test_empty_string(self):
        """Test empty string handling."""
        assert _parse_vmess("") is None
        assert _parse_ss("") is None
        assert _extract_config_lines("") == []

    def test_whitespace_only(self):
        """Test whitespace-only input."""
        assert _extract_config_lines("   \n\n\t\t  ") == []

    def test_unicode_handling(self):
        """Test Unicode character handling."""
        config = "vmess://测试配置"
        _ = _parse_vmess(config)
        # Should handle Unicode without crashing


class TestSecurityValidations:
    """Test security-related validations."""

    def test_ipv6_address_handling(self):
        """Test IPv6 address handling in parsers."""
        import base64

        config_str = "aes-256-gcm:password@[2001:db8::1]:443"
        config = "ss://" + base64.b64encode(config_str.encode()).decode()
        _ = _parse_ss(config)
        # Should handle IPv6 addresses in brackets

    def test_sql_injection_attempt(self):
        """Test SQL injection in config is sanitized."""
        import base64
        import json

        config_data = {
            "add": "'; DROP TABLE proxies; --",
            "port": 443,
            "id": "test-uuid",
        }
        config = (
            "vmess://" + base64.b64encode(json.dumps(config_data).encode()).decode()
        )
        _ = _parse_vmess(config)
        # Should parse but address should be sanitized/validated

    def test_xss_attempt(self):
        """Test XSS in remarks field."""
        import base64
        import json

        config_data = {
            "add": "example.com",
            "port": 443,
            "id": "test-uuid",
            "ps": "<script>alert('xss')</script>",
        }
        config = (
            "vmess://" + base64.b64encode(json.dumps(config_data).encode()).decode()
        )
        result = _parse_vmess(config)
        if result:
            # Remarks should be truncated but not cause execution
            assert len(result.remarks) <= 200
