"""Comprehensive tests for Shadowsocks parser."""

import pytest
import base64
from configstream.parsers.shadowsocks import parse_ss, parse_ss2022


class TestParseSS:
    """Test cases for parse_ss function."""

    def test_parse_ss_valid_base64_userinfo(self):
        """Test parsing SS with base64 encoded userinfo."""
        # method:password encoded as base64
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password123").decode()
        uri = f"ss://{user_info}@1.2.3.4:8388#TestServer"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert proxy.address == "1.2.3.4"
        assert proxy.port == 8388
        assert proxy.protocol == "shadowsocks"
        assert proxy.details["method"] == "aes-256-gcm"
        assert proxy.details["password"] == "password123"
        assert proxy.remarks == "TestServer"

    def test_parse_ss_sip002_format(self):
        """Test parsing SS in SIP002 format (full base64)."""
        # Full string encoded: method:password@host:port
        full_str = "aes-256-gcm:mypass@example.com:8388"
        encoded = base64.urlsafe_b64encode(full_str.encode()).decode()
        uri = f"ss://{encoded}#SIP002"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert proxy.address == "example.com"
        assert proxy.port == 8388
        assert proxy.details["method"] == "aes-256-gcm"
        assert proxy.details["password"] == "mypass"
        assert proxy.remarks == "SIP002"

    def test_parse_ss_plain_text_userinfo(self):
        """Test parsing SS with plain text userinfo (not base64)."""
        uri = "ss://aes-128-gcm:pass123@192.168.1.1:8388#Plain"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert proxy.address == "192.168.1.1"
        assert proxy.port == 8388
        assert proxy.details["method"] == "aes-128-gcm"
        assert proxy.details["password"] == "pass123"

    def test_parse_ss_with_query_params(self):
        """Test parsing SS with query parameters."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        # Correct format: #remark?query=params
        uri = f"ss://{user_info}@1.2.3.4:8388#Server?plugin=obfs"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert proxy.address == "1.2.3.4"
        assert "plugin" in proxy.details

    def test_parse_ss_ipv6_address(self):
        """Test parsing SS with IPv6 address."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        uri = f"ss://{user_info}@[2001:db8::1]:8388#IPv6"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert proxy.address == "2001:db8::1"
        assert proxy.port == 8388

    def test_parse_ss_without_remark(self):
        """Test parsing SS without remark."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        uri = f"ss://{user_info}@1.2.3.4:8388"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert proxy.remarks == ""

    def test_parse_ss_url_encoded_remark(self):
        """Test parsing SS with URL encoded remark."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        uri = f"ss://{user_info}@1.2.3.4:8388#My%20Server%20%231"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert proxy.remarks == "My Server #1"

    def test_parse_ss_invalid_protocol(self):
        """Test that parse_ss returns None for invalid protocol."""
        proxy = parse_ss("http://example.com")
        assert proxy is None

        proxy = parse_ss("vmess://abcdef")
        assert proxy is None

    def test_parse_ss_invalid_base64_sip002(self):
        """Test parsing invalid base64 in SIP002 format."""
        uri = "ss://invalid_base64_!!!#Test"
        proxy = parse_ss(uri)
        # Should handle gracefully and return None
        assert proxy is None

    def test_parse_ss_missing_at_symbol(self):
        """Test parsing SS without @ symbol in SIP002 format."""
        # Encode string without @
        encoded = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        uri = f"ss://{encoded}#NoAt"

        proxy = parse_ss(uri)
        assert proxy is None

    def test_parse_ss_missing_colon_in_userinfo(self):
        """Test parsing SS with missing colon in userinfo."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm-no-password").decode()
        uri = f"ss://{user_info}@1.2.3.4:8388"

        proxy = parse_ss(uri)
        assert proxy is None

    def test_parse_ss_missing_colon_in_hostinfo(self):
        """Test parsing SS with missing colon in hostinfo (no port)."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        uri = f"ss://{user_info}@example.com"

        proxy = parse_ss(uri)
        assert proxy is None

    def test_parse_ss_invalid_port(self):
        """Test parsing SS with invalid port."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        uri = f"ss://{user_info}@1.2.3.4:notaport"

        proxy = parse_ss(uri)
        assert proxy is None

    def test_parse_ss_port_out_of_range(self):
        """Test parsing SS with port out of valid range."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()

        # Port too high
        uri = f"ss://{user_info}@1.2.3.4:99999"
        proxy = parse_ss(uri)
        assert proxy is None

        # Port too low
        uri = f"ss://{user_info}@1.2.3.4:0"
        proxy = parse_ss(uri)
        assert proxy is None

    def test_parse_ss_empty_host(self):
        """Test parsing SS with empty host."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        uri = f"ss://{user_info}@:8388"

        proxy = parse_ss(uri)
        assert proxy is None

    def test_parse_ss_with_binascii_error(self):
        """Test parsing SS that triggers binascii error."""
        # Malformed base64 that can't be decoded
        uri = "ss://!!!invalid!!!@1.2.3.4:8388"

        proxy = parse_ss(uri)
        # Should handle gracefully
        assert proxy is None

    def test_parse_ss_with_value_error(self):
        """Test parsing SS that triggers ValueError."""
        # Empty config
        proxy = parse_ss("")
        assert proxy is None

    def test_parse_ss_with_index_error(self):
        """Test parsing SS that triggers IndexError."""
        uri = "ss://"
        proxy = parse_ss(uri)
        assert proxy is None

    def test_parse_ss_complex_password(self):
        """Test parsing SS with complex password containing special characters."""
        password = "p@ssw0rd!#$%^&*()"
        user_info = base64.urlsafe_b64encode(
            f"aes-256-gcm:{password}".encode()
        ).decode()
        uri = f"ss://{user_info}@1.2.3.4:8388"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert proxy.details["password"] == password

    def test_parse_ss_multiple_colons_in_password(self):
        """Test parsing SS with password containing colons."""
        password = "pass:word:with:colons"
        user_info = base64.urlsafe_b64encode(
            f"aes-256-gcm:{password}".encode()
        ).decode()
        uri = f"ss://{user_info}@1.2.3.4:8388"

        proxy = parse_ss(uri)

        assert proxy is not None
        # Password should include all parts after first colon
        assert proxy.details["password"] == password

    def test_parse_ss_with_plugin_params(self):
        """Test parsing SS with plugin parameters in query string."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        uri = f"ss://{user_info}@1.2.3.4:8388#Remark?plugin=v2ray-plugin&mode=websocket"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert "plugin" in proxy.details
        assert "mode" in proxy.details

    def test_parse_ss_empty_method(self):
        """Test parsing SS with empty method."""
        user_info = base64.urlsafe_b64encode(b":password").decode()
        uri = f"ss://{user_info}@1.2.3.4:8388"

        proxy = parse_ss(uri)

        assert proxy is not None
        # Should still parse, method will be empty string

    def test_parse_ss_rsplit_for_port(self):
        """Test that parser uses rsplit for port (handles IPv6 correctly)."""
        # IPv6 address with multiple colons
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        uri = f"ss://{user_info}@2001:db8::1:8388"

        proxy = parse_ss(uri)

        # Should use rsplit to get port correctly
        assert proxy is not None
        assert proxy.port == 8388


class TestParseSS2022:
    """Test cases for parse_ss2022 function."""

    def test_parse_ss2022_valid(self):
        """Test parsing valid SS2022 URL."""
        # Create valid ss:// URL first
        user_info = base64.urlsafe_b64encode(
            b"2022-blake3-aes-256-gcm:password"
        ).decode()
        ss_uri = f"ss://{user_info}@1.2.3.4:8388#SS2022Server"

        # Convert to ss2022://
        ss2022_uri = "ss2022://" + ss_uri[5:]

        proxy = parse_ss2022(ss2022_uri)

        assert proxy is not None
        assert proxy.address == "1.2.3.4"
        assert proxy.port == 8388
        assert proxy.protocol == "ss2022"
        assert proxy.config == ss2022_uri
        assert proxy.remarks == "SS2022Server"

    def test_parse_ss2022_with_base64(self):
        """Test parsing SS2022 with base64 encoded data."""
        full_str = "2022-blake3-aes-256-gcm:mypass@example.com:8388"
        encoded = base64.urlsafe_b64encode(full_str.encode()).decode()
        uri = f"ss2022://{encoded}#TestSS2022"

        proxy = parse_ss2022(uri)

        assert proxy is not None
        assert proxy.protocol == "ss2022"
        assert proxy.address == "example.com"
        assert proxy.port == 8388

    def test_parse_ss2022_invalid_protocol(self):
        """Test that parse_ss2022 returns None for invalid protocol."""
        proxy = parse_ss2022("ss://test@1.2.3.4:8388")
        assert proxy is None

        proxy = parse_ss2022("http://example.com")
        assert proxy is None

    def test_parse_ss2022_delegates_to_parse_ss(self):
        """Test that parse_ss2022 delegates to parse_ss correctly."""
        user_info = base64.urlsafe_b64encode(b"method:password").decode()
        uri = f"ss2022://{user_info}@1.2.3.4:8388"

        proxy = parse_ss2022(uri)

        assert proxy is not None
        assert proxy.protocol == "ss2022"

    def test_parse_ss2022_preserves_original_config(self):
        """Test that parse_ss2022 preserves original config URL."""
        user_info = base64.urlsafe_b64encode(b"method:password").decode()
        original_uri = f"ss2022://{user_info}@1.2.3.4:8388#Original"

        proxy = parse_ss2022(original_uri)

        assert proxy is not None
        assert proxy.config == original_uri
        assert "ss2022://" in proxy.config

    def test_parse_ss2022_invalid_underlying_format(self):
        """Test parse_ss2022 with invalid underlying format."""
        uri = "ss2022://invalid_format_here"

        proxy = parse_ss2022(uri)
        assert proxy is None

    def test_parse_ss2022_exception_handling(self):
        """Test that parse_ss2022 handles exceptions gracefully."""
        # Various invalid formats
        invalid_uris = [
            "ss2022://",
            "ss2022://!!!",
            "ss2022://malformed",
        ]

        for uri in invalid_uris:
            proxy = parse_ss2022(uri)
            assert proxy is None

    def test_parse_ss2022_with_ipv6(self):
        """Test parsing SS2022 with IPv6 address."""
        user_info = base64.urlsafe_b64encode(b"method:password").decode()
        uri = f"ss2022://{user_info}@[2001:db8::1]:8388"

        proxy = parse_ss2022(uri)

        assert proxy is not None
        assert proxy.protocol == "ss2022"
        assert proxy.address == "2001:db8::1"

    def test_parse_ss2022_with_query_params(self):
        """Test parsing SS2022 with query parameters."""
        user_info = base64.urlsafe_b64encode(b"method:password").decode()
        uri = f"ss2022://{user_info}@1.2.3.4:8388#Remark?plugin=test"

        proxy = parse_ss2022(uri)

        assert proxy is not None
        assert proxy.protocol == "ss2022"

    def test_parse_ss2022_empty_string(self):
        """Test parsing empty SS2022 string."""
        proxy = parse_ss2022("")
        assert proxy is None

    def test_parse_ss2022_none_from_parse_ss(self):
        """Test parse_ss2022 when parse_ss returns None."""
        # Create an invalid ss:// URL that parse_ss will reject
        uri = "ss2022://invalid@:0"

        proxy = parse_ss2022(uri)
        assert proxy is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_parse_ss_very_long_password(self):
        """Test parsing SS with very long password."""
        password = "a" * 1000
        user_info = base64.urlsafe_b64encode(
            f"aes-256-gcm:{password}".encode()
        ).decode()
        uri = f"ss://{user_info}@1.2.3.4:8388"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert len(proxy.details["password"]) == 1000

    def test_parse_ss_unicode_in_remark(self):
        """Test parsing SS with unicode characters in remark."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        # URL encode unicode
        import urllib.parse

        remark = "服务器测试"
        encoded_remark = urllib.parse.quote(remark)
        uri = f"ss://{user_info}@1.2.3.4:8388#{encoded_remark}"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert proxy.remarks == remark

    def test_parse_ss_minimum_valid_port(self):
        """Test parsing SS with minimum valid port (1)."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        uri = f"ss://{user_info}@1.2.3.4:1"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert proxy.port == 1

    def test_parse_ss_maximum_valid_port(self):
        """Test parsing SS with maximum valid port (65535)."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        uri = f"ss://{user_info}@1.2.3.4:65535"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert proxy.port == 65535

    def test_parse_ss_with_fragment_and_query(self):
        """Test parsing SS with both fragment and query string."""
        user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode()
        uri = f"ss://{user_info}@1.2.3.4:8388#Remark?plugin=v2ray&mode=ws"

        proxy = parse_ss(uri)

        assert proxy is not None
        assert proxy.remarks == "Remark"
        # Query params should be parsed into details

    def test_parse_ss_base64_padding_variations(self):
        """Test parsing SS with various base64 padding scenarios."""
        # Base64 strings with different padding
        passwords = ["p", "pa", "pas", "pass"]

        for password in passwords:
            user_info = base64.urlsafe_b64encode(
                f"aes-256-gcm:{password}".encode()
            ).decode()
            uri = f"ss://{user_info}@1.2.3.4:8388"

            proxy = parse_ss(uri)
            assert proxy is not None
            assert proxy.details["password"] == password
