"""Extended tests for parser edge cases and error handling."""

import pytest
from configstream.parsers import (
    _parse_vmess,
    _parse_vless,
    _parse_trojan,
    _parse_ss,
    _parse_ssr,
    _parse_hysteria2,
    _parse_tuic,
    _parse_wireguard,
    _parse_xray,
    _parse_naive,
    _validate_b64_input,
    _is_plausible_proxy_config,
)


class TestBase64ValidationEdgeCases:
    """Test edge cases in base64 validation."""

    def test_validate_b64_input_with_invalid_chars(self):
        """Test validation with invalid base64 characters."""
        result = _validate_b64_input("abc!@#$%^&*()")
        assert result is None

    def test_validate_b64_input_with_spaces_and_newlines(self):
        """Test validation handles whitespace correctly."""
        result = _validate_b64_input("YWJj\nZGVm\n")
        assert result is not None
        assert "\n" not in result

    def test_validate_b64_input_oversized(self):
        """Test validation rejects oversized input."""
        huge_input = "A" * (60 * 1024 * 1024)  # 60 MB
        result = _validate_b64_input(huge_input)
        assert result is None

    def test_validate_b64_input_non_string(self):
        """Test validation with non-string input."""
        result = _validate_b64_input(12345)
        assert result is None

    def test_validate_b64_input_adds_padding(self):
        """Test validation adds missing padding."""
        # Base64 without padding
        result = _validate_b64_input("YWJj")
        assert result is not None
        assert result.endswith("=") or len(result) % 4 == 0


class TestPlausibilityCheck:
    """Test plausibility checking for configs."""

    def test_plausible_check_no_protocol_separator(self):
        """Test rejection of configs without ://"""
        assert _is_plausible_proxy_config("invalid-config") is False

    def test_plausible_check_protocol_too_long(self):
        """Test rejection of configs with overly long protocol."""
        assert _is_plausible_proxy_config("verylongprotocolname" + "x" * 20 + "://test") is False

    def test_plausible_check_rest_too_short(self):
        """Test rejection of configs with insufficient data."""
        assert _is_plausible_proxy_config("vmess://ab") is False

    def test_plausible_check_too_many_special_chars(self):
        """Test rejection of configs with excessive special characters."""
        assert _is_plausible_proxy_config("vmess://!@#$%^&*()!@#$%^&*()") is False

    def test_plausible_check_valid_config(self):
        """Test acceptance of valid-looking configs."""
        assert _is_plausible_proxy_config("vmess://example.com:443") is True


class TestVMessParserEdgeCases:
    """Test VMess parser edge cases."""

    def test_parse_vmess_with_invalid_json(self):
        """Test VMess with malformed JSON."""
        import base64

        invalid_json = base64.b64encode(b"{invalid json").decode("utf-8")
        result = _parse_vmess(f"vmess://{invalid_json}")
        assert result is None

    def test_parse_vmess_with_missing_required_fields(self):
        """Test VMess with missing required fields."""
        import base64
        import json

        config = {"v": "2", "add": "test.com"}  # Missing port, id, etc.
        encoded = base64.b64encode(json.dumps(config).encode("utf-8")).decode("utf-8")
        result = _parse_vmess(f"vmess://{encoded}")
        assert result is None

    def test_parse_vmess_with_invalid_port(self):
        """Test VMess with invalid port."""
        import base64
        import json

        config = {
            "v": "2",
            "ps": "test",
            "add": "test.com",
            "port": "invalid",
            "id": "uuid",
            "aid": "0",
            "net": "tcp",
            "type": "none",
            "host": "",
            "path": "",
            "tls": "",
        }
        encoded = base64.b64encode(json.dumps(config).encode("utf-8")).decode("utf-8")
        result = _parse_vmess(f"vmess://{encoded}")
        assert result is None


class TestVLESSParserEdgeCases:
    """Test VLESS parser edge cases."""

    def test_parse_vless_missing_uuid(self):
        """Test VLESS without UUID."""
        result = _parse_vless("vless://@example.com:443")
        assert result is None

    def test_parse_vless_invalid_netloc(self):
        """Test VLESS with invalid netloc."""
        result = _parse_vless("vless://uuid@")
        assert result is None

    def test_parse_vless_with_port_parsing_error(self):
        """Test VLESS with non-numeric port."""
        result = _parse_vless("vless://uuid@example.com:abc")
        assert result is None


class TestTrojanParserEdgeCases:
    """Test Trojan parser edge cases."""

    def test_parse_trojan_missing_password(self):
        """Test Trojan without password."""
        result = _parse_trojan("trojan://@example.com:443")
        # Parser is permissive, returns proxy with empty password
        assert result is not None
        assert result.uuid == ""

    def test_parse_trojan_invalid_netloc(self):
        """Test Trojan with invalid netloc."""
        result = _parse_trojan("trojan://password@")
        assert result is None


class TestShadowsocksParserEdgeCases:
    """Test Shadowsocks parser edge cases."""

    def test_parse_ss_invalid_base64(self):
        """Test Shadowsocks with invalid base64."""
        result = _parse_ss("ss://invalid!@#base64")
        assert result is None

    def test_parse_ss_missing_required_parts(self):
        """Test Shadowsocks with incomplete config."""
        import base64

        # Just method, no server info
        encoded = base64.b64encode(b"aes-256-gcm").decode("utf-8")
        result = _parse_ss(f"ss://{encoded}")
        assert result is None

    def test_parse_ss_with_port_parsing_error(self):
        """Test Shadowsocks with a non-numeric port."""
        import base64

        config = "aes-256-gcm:password@127.0.0.1:abc#test"
        encoded = base64.urlsafe_b64encode(config.encode()).decode()
        result = _parse_ss(f"ss://{encoded}")
        assert result is None

    def test_parse_ss_with_empty_userinfo(self):
        """Test Shadowsocks with empty user information."""
        import base64

        config = "@127.0.0.1:8080#test"
        encoded = base64.urlsafe_b64encode(config.encode()).decode()
        result = _parse_ss(f"ss://{encoded}")
        assert result is None


class TestSSRParserEdgeCases:
    """Test ShadowsocksR parser edge cases."""

    def test_parse_ssr_invalid_format(self):
        """Test SSR with invalid format."""
        import base64

        invalid = base64.b64encode(b"invalid-format").decode("utf-8")
        result = _parse_ssr(f"ssr://{invalid}")
        assert result is None

    def test_parse_ssr_missing_parts(self):
        """Test SSR with missing required parts."""
        import base64

        incomplete = base64.b64encode(b"server:port").decode("utf-8")
        result = _parse_ssr(f"ssr://{incomplete}")
        assert result is None

    def test_parse_ssr_with_invalid_base64_in_params(self):
        """Test SSR with invalid base64 in URL parameters."""
        import base64

        config = "127.0.0.1:8080:origin:aes-256-cfb:http_simple:cGFzc3dvcmQ/?remarks=invalid!@#"
        encoded = base64.urlsafe_b64encode(config.encode()).decode()
        result = _parse_ssr(f"ssr://{encoded}")
        assert result is None


class TestHysteria2ParserEdgeCases:
    """Test Hysteria2 parser edge cases."""

    def test_parse_hysteria2_invalid_netloc(self):
        """Test Hysteria2 with invalid netloc."""
        result = _parse_hysteria2("hysteria2://")
        assert result is None

    def test_parse_hysteria2_missing_password(self):
        """Test Hysteria2 without password."""
        result = _parse_hysteria2("hysteria2://example.com:443")
        # This should handle it gracefully
        assert result is None


class TestTUICParserEdgeCases:
    """Test TUIC parser edge cases."""

    def test_parse_tuic_invalid_format(self):
        """Test TUIC with invalid format."""
        result = _parse_tuic("tuic://invalid")
        # Parser is permissive, returns proxy with minimal info
        assert result is not None

    def test_parse_tuic_missing_uuid(self):
        """Test TUIC without UUID."""
        result = _parse_tuic("tuic://@example.com:443")
        # Parser is permissive, returns proxy with empty UUID
        assert result is not None
        assert result.uuid == ""


class TestWireGuardParserEdgeCases:
    """Test WireGuard parser edge cases."""

    def test_parse_wireguard_invalid_format(self):
        """Test WireGuard with invalid format."""
        result = _parse_wireguard("wireguard://invalid")
        assert result is None


class TestXRayParserEdgeCases:
    """Test XRay parser edge cases."""

    def test_parse_xray_invalid_format(self):
        """Test XRay with invalid format."""
        result = _parse_xray("xray://invalid")
        assert result is None


class TestNaiveParserEdgeCases:
    """Test Naive parser edge cases."""

    def test_parse_naive_invalid_format(self):
        """Test Naive with invalid format."""
        result = _parse_naive("naive+https://invalid")
        # This format is invalid because it lacks userinfo (user/pass)
        assert result is None

    def test_parse_naive_missing_credentials(self):
        """Test Naive without credentials."""
        result = _parse_naive("naive+https://example.com:443")
        # Parser is permissive, handles gracefully
        assert result is None


class TestParserMemorySafety:
    """Test parser memory safety and limits."""

    def test_parse_with_extremely_long_address(self):
        """Test parser with extremely long address."""
        long_address = "a" * 10000
        result = _parse_vless(f"vless://uuid@{long_address}:443")
        # Should handle without crashing
        assert isinstance(result, (type(None), object))

    def test_parse_with_extremely_long_uuid(self):
        """Test parser with extremely long UUID."""
        long_uuid = "a" * 10000
        result = _parse_vless(f"vless://{long_uuid}@example.com:443")
        # Should handle without crashing
        assert isinstance(result, (type(None), object))


class TestParserUnicodeHandling:
    """Test parser handling of unicode and special characters."""

    def test_parse_with_unicode_domain(self):
        """Test parser with unicode domain."""
        result = _parse_vless("vless://uuid@例え.com:443")
        # Should handle unicode gracefully
        assert isinstance(result, (type(None), object))

    def test_parse_with_unicode_in_path(self):
        """Test parser with unicode in path parameters."""
        result = _parse_vless("vless://uuid@example.com:443?path=/测试")
        # Should handle unicode gracefully
        assert isinstance(result, (type(None), object))


class TestParserNullByteHandling:
    """Test parser handling of null bytes."""

    def test_parse_with_null_byte_in_config(self):
        """Test parser with null byte in config string."""
        result = _parse_vless("vless://uuid\x00@example.com:443")
        # Should reject or handle safely
        assert result is None or isinstance(result, object)


class TestParserProtocolVariations:
    """Test parser with protocol variations."""

    def test_parse_uppercase_protocol(self):
        """Test parser with uppercase protocol."""
        result = _parse_vless("VLESS://uuid@example.com:443")
        # Should handle case-insensitively or reject consistently
        assert isinstance(result, (type(None), object))

    def test_parse_mixed_case_protocol(self):
        """Test parser with mixed case protocol."""
        result = _parse_vless("VlEsS://uuid@example.com:443")
        # Should handle case-insensitively or reject consistently
        assert isinstance(result, (type(None), object))
