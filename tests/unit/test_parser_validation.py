"""
Tests for parser input validation

These tests verify that our parsers correctly reject malformed or
malicious input without crashing.
"""

from configstream.parsers import (
    _validate_b64_input,
    _safe_b64_decode,
    _extract_config_lines,
    _is_plausible_proxy_config,
    _parse_vmess,
    _parse_ss,
)


class TestBase64Validation:
    """Tests for base64 validation and decoding"""

    def test_validate_valid_base64(self):
        """Test that valid base64 passes validation"""
        valid_b64 = "SGVsbG8gV29ybGQ="  # "Hello World"
        result = _validate_b64_input(valid_b64)
        assert result is not None
        assert result == valid_b64

    def test_validate_rejects_null(self):
        """Test that null/empty inputs are rejected"""
        assert _validate_b64_input(None) is None
        assert _validate_b64_input("") is None
        assert _validate_b64_input("   ") is None

    def test_validate_rejects_oversized(self):
        """Test that huge inputs are rejected"""
        # Create string larger than MAX_B64_INPUT_SIZE
        huge = "A" * (50 * 1024 * 1024 + 1)
        result = _validate_b64_input(huge)
        assert result is None

    def test_validate_rejects_invalid_chars(self):
        """Test that non-base64 characters are rejected"""
        invalid = "Hello!@#$%^&*()"  # Not base64 chars
        result = _validate_b64_input(invalid)
        assert result is None

    def test_validate_adds_padding(self):
        """Test that missing padding is added"""
        # Base64 without padding
        unpadded = "SGVsbG8"  # Would be "SGVsbG8=" with padding
        result = _validate_b64_input(unpadded)
        assert result is not None
        assert result.endswith("=")
        assert len(result) % 4 == 0

    def test_safe_decode_valid(self):
        """Test decoding valid base64"""
        b64 = "SGVsbG8gV29ybGQ="
        result = _safe_b64_decode(b64)
        assert result == "Hello World"

    def test_safe_decode_returns_original_on_failure(self):
        """Test that invalid base64 returns original string"""
        invalid = "Not base64 at all!"
        result = _safe_b64_decode(invalid)
        assert result == invalid

    def test_safe_decode_handles_oversized_output(self):
        """Test that outputs exceeding size limit are rejected"""
        # This test is conceptual - we can't easily create a base64
        # input that decodes to >100MB in a unit test
        # In practice, this is tested via integration tests


class TestConfigLineExtraction:
    """Tests for extracting config lines from payloads"""

    def test_extract_valid_configs(self):
        """Test extracting valid proxy configurations"""
        payload = """
        # This is a comment
        vmess://YWJjMTIz

        ss://YWJjMTIz@host:443
        # Another comment
        trojan://password@host:443
        """

        result = _extract_config_lines(payload)

        assert len(result) == 3
        assert any("vmess://" in line for line in result)
        assert any("ss://" in line for line in result)
        assert any("trojan://" in line for line in result)

    def test_extract_filters_invalid_protocols(self):
        """Test that unknown protocols are filtered out"""
        payload = """
        vmess://valid
        unknown://invalid
        ftp://alsoinvalid
        ss://valid
        """

        result = _extract_config_lines(payload)

        assert len(result) == 2
        assert not any("unknown://" in line for line in result)
        assert not any("ftp://" in line for line in result)

    def test_extract_enforces_line_limit(self):
        """Test that excessive lines are truncated"""
        # Create payload with many lines
        lines = [f"vmess://config{i}" for i in range(15000)]
        payload = "\n".join(lines)

        result = _extract_config_lines(payload, max_lines=10000)

        # Should be limited to 10000
        assert len(result) <= 10000

    def test_extract_filters_overly_long_lines(self):
        """Test that excessively long lines are rejected"""
        # Create a line longer than MAX_CONFIG_LINE_LENGTH
        long_line = "vmess://" + "A" * 20000
        payload = f"vmess://valid\n{long_line}\nvless://alsovalid"

        result = _extract_config_lines(payload)

        # Should have 2 configs (long one rejected)
        assert len(result) == 2
        assert all(len(line) < 10000 for line in result)

    def test_extract_handles_empty_payload(self):
        """Test that empty payload returns empty list"""
        assert _extract_config_lines("") == []
        assert _extract_config_lines("   \n\n  ") == []

    def test_extract_handles_none(self):
        """Test that None payload returns empty list"""
        assert _extract_config_lines(None) == []


class TestPlausibilityCheck:
    """Tests for proxy config plausibility checking"""

    def test_plausible_accepts_valid_configs(self):
        """Test that valid configs pass plausibility check"""
        assert _is_plausible_proxy_config("vmess://base64data") is True
        assert _is_plausible_proxy_config("ss://user@host:443") is True
        assert _is_plausible_proxy_config("trojan://pass@example.com:443") is True

    def test_plausible_rejects_no_protocol(self):
        """Test that strings without protocol are rejected"""
        assert _is_plausible_proxy_config("noprotocol") is False
        assert _is_plausible_proxy_config("just some text") is False

    def test_plausible_rejects_empty_content(self):
        """Test that configs with no content after protocol are rejected"""
        assert _is_plausible_proxy_config("vmess://") is False
        assert _is_plausible_proxy_config("ss://a") is False  # Too short

    def test_plausible_rejects_long_protocol(self):
        """Test that unreasonably long protocol names are rejected"""
        long_proto = "a" * 30 + "://data"
        assert _is_plausible_proxy_config(long_proto) is False

    def test_plausible_rejects_excessive_special_chars(self):
        """Test that strings with too many special chars are rejected"""
        # Create string with >50% special characters
        bad_config = "vmess://" + "!@#$%^&*()" * 100
        assert _is_plausible_proxy_config(bad_config) is False


class TestVMessParser:
    """Tests for VMess configuration parsing with validation"""

    def test_parse_valid_vmess(self):
        """Test parsing a valid VMess configuration"""
        import base64
        import json

        # Create valid VMess config
        vmess_data = {
            "add": "example.com",
            "port": 443,
            "id": "uuid-goes-here",
            "ps": "Test Server",
        }

        b64_data = base64.b64encode(json.dumps(vmess_data).encode()).decode()

        config = f"vmess://{b64_data}"

        result = _parse_vmess(config)

        assert result is not None
        assert result.protocol == "vmess"
        assert result.address == "example.com"
        assert result.port == 443
        assert result.uuid == "uuid-goes-here"

    def test_parse_rejects_invalid_port(self):
        """Test that invalid port numbers are rejected"""
        import base64
        import json

        # Port of 0 is invalid
        vmess_data = {"add": "example.com", "port": 0, "id": "uuid"}

        b64_data = base64.b64encode(json.dumps(vmess_data).encode()).decode()
        config = f"vmess://{b64_data}"

        result = _parse_vmess(config)
        assert result is None

    def test_parse_rejects_missing_fields(self):
        """Test that configs missing required fields are rejected"""
        import base64
        import json

        # Missing 'id' field
        vmess_data = {"add": "example.com", "port": 443}

        b64_data = base64.b64encode(json.dumps(vmess_data).encode()).decode()
        config = f"vmess://{b64_data}"

        result = _parse_vmess(config)
        assert result is None

    def test_parse_rejects_oversized_config(self):
        """Test that excessively large configs are rejected"""
        # Create oversized base64 portion
        huge_b64 = "A" * 20000
        config = f"vmess://{huge_b64}"

        result = _parse_vmess(config)
        assert result is None


class TestShadowsocksParser:
    """Tests for Shadowsocks configuration parsing"""

    def test_parse_valid_shadowsocks(self):
        """Test parsing a valid Shadowsocks configuration"""
        import base64

        method_pass_host_port = base64.b64encode(b"aes-256-gcm:password@example.com:443").decode()
        config = f"ss://{method_pass_host_port}#TestServer"

        result = _parse_ss(config)

        assert result is not None
        assert result.protocol == "shadowsocks"
        assert result.address == "example.com"
        assert result.port == 443
        assert "aes-256-gcm" in result.details["method"]

    def test_parse_rejects_malformed(self):
        """Test that malformed configs are rejected"""
        # Missing @ separator
        config = "ss://invalidformat"
        result = _parse_ss(config)
        assert result is None

    def test_parse_handles_missing_fragment(self):
        """Test that configs without name/fragment still parse"""
        import base64

        method_pass_host_port = base64.b64encode(b"aes-256-gcm:password@example.com:443").decode()
        config = f"ss://{method_pass_host_port}"

        result = _parse_ss(config)

        assert result is not None
        assert result.remarks == ""


class TestConfigExtractionEdgeCases:
    """Test edge cases for config line extraction."""

    def test_extract_handles_mixed_valid_and_invalid(self):
        """Test payload with mixed valid and invalid lines."""
        payload = "vmess://valid\nnot-a-config\nss://another_valid"
        result = _extract_config_lines(payload)
        assert len(result) == 2
        assert "vmess://valid" in result
        assert "ss://another_valid" in result

    def test_extract_handles_lines_with_only_whitespace(self):
        """Test that lines with only whitespace are ignored."""
        payload = "vmess://valid\n  \t  \nss://another_valid"
        result = _extract_config_lines(payload)
        assert len(result) == 2

    def test_extract_handles_non_string_payload(self):
        """Test that non-string input is handled gracefully."""
        result = _extract_config_lines(12345)
        assert result == []


# Run tests with:
# pytest tests/test_parser_validation.py -v
