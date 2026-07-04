# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for decoder utilities (safe_b64_decode, validate_b64_input)."""

from configstream.parsers.decoders import validate_b64_input, safe_b64_decode


class TestValidateB64Input:
    """Tests for validate_b64_input."""

    def test_valid_base64(self):
        """Standard base64 string."""
        result = validate_b64_input("aGVsbG8=")
        assert result is not None
        assert "=" in result  # Should have padding

    def test_urlsafe_base64(self):
        """URL-safe base64 with - and _."""
        result = validate_b64_input("aGVsbG8td29ybGQ=")
        assert result is not None

    def test_unpadded_base64(self):
        """Base64 without padding should get padding added."""
        result = validate_b64_input("aGVsbG8")
        assert result is not None
        assert result.endswith("=")

    def test_base64_with_whitespace(self):
        """Base64 with whitespace should be cleaned."""
        result = validate_b64_input("a G Vs b G 8=")
        assert result is not None

    def test_empty_string(self):
        """Empty string should return None."""
        assert validate_b64_input("") is None

    def test_none_input(self):
        """None should return None."""
        # noinspection PyTypeChecker
        assert validate_b64_input(None) is None  # type: ignore

    def test_html_input_rejected(self):
        """HTML input should be rejected."""
        assert validate_b64_input("<html>") is None

    def test_json_input_rejected(self):
        """JSON object input should be rejected."""
        assert validate_b64_input('{"key": "value"}') is None

    def test_json_array_input_rejected(self):
        """JSON array input should be rejected."""
        assert validate_b64_input("[1, 2, 3]") is None

    def test_colon_in_non_padded_rejected(self):
        """Colon in non-padded base64 should be rejected."""
        assert validate_b64_input("aes-256-gcm:password") is None

    def test_high_noise_rejected(self):
        """High proportion of invalid chars should be rejected."""
        assert validate_b64_input("ABC" + "!" * 100) is None

    def test_url_encoded_base64(self):
        """URL-encoded base64 (%3D for =) should be unescaped."""
        result = validate_b64_input("aGVsbG8%3D")
        assert result is not None
        assert result.rstrip("=").endswith("aGVsbG8") or result == "aGVsbG8="

    def test_null_bytes_rejected(self):
        """String with null bytes should be rejected."""
        assert validate_b64_input("aGVs\x00bG8=") is None

    def test_long_base64_valid(self):
        """Long but valid base64 should pass."""
        long_b64 = "a" * 1000 + "="
        result = validate_b64_input(long_b64)
        assert result is not None

    def test_short_base64_valid(self):
        """Very short valid base64 should pass."""
        assert validate_b64_input("YQ==") is not None  # "a"


class TestSafeB64Decode:
    """Tests for safe_b64_decode."""

    def test_decode_standard(self):
        """Standard base64 decode."""
        result = safe_b64_decode("aGVsbG8=")
        assert result == "hello"

    def test_decode_unpadded(self):
        """Unpadded base64 decode."""
        result = safe_b64_decode("aGVsbG8")
        assert result == "hello"

    def test_decode_urlsafe(self):
        """URL-safe base64 decode with - and _."""
        import base64

        encoded = base64.urlsafe_b64encode(b"hello world").decode().rstrip("=")
        result = safe_b64_decode(encoded)
        assert result == "hello world"

    def test_decode_empty_string(self):
        """Empty string should return None."""
        assert safe_b64_decode("") is None

    def test_decode_none(self):
        """None should return None."""
        # noinspection PyTypeChecker
        assert safe_b64_decode(None) is None  # type: ignore

    def test_decode_garbage(self):
        """Garbage input should return None."""
        assert safe_b64_decode("!!!not base64!!!") is None

    def test_decode_json(self):
        """JSON input should return None."""
        assert safe_b64_decode('{"key": "val"}') is None

    def test_decode_very_long_input(self):
        """Very long input should still be decoded when MAX_B64_INPUT_SIZE is 0 (unlimited)."""
        import base64

        # Create a genuinely long valid base64 string (10KB of 'a's)
        original = b"a" * 10000
        long_b64 = base64.b64encode(original).decode()
        result = safe_b64_decode(long_b64)
        assert result is not None
        assert len(result) == 10000
        assert result == "a" * 10000

    def test_decode_mixed_alphabets(self):
        """Mixed standard and URL-safe alphabet."""
        result = safe_b64_decode("YSBtaXhlZCBzdHJpbmc/")
        assert result is not None

    def test_decode_with_newlines(self):
        """Base64 with embedded newlines."""
        result = safe_b64_decode("aGVs\nbG8=")
        assert result == "hello"

    def test_decode_utf8_content(self):
        """Base64 encoded UTF-8 content."""
        import base64

        encoded = base64.b64encode("héllo wörld".encode()).decode()
        result = safe_b64_decode(encoded)
        assert result is not None
        assert "héllo" in result

    def test_decode_vmess_payload_style(self):
        """VMess-style JSON-in-base64 payload."""
        import base64

        payload = '{"add":"1.2.3.4","port":443,"id":"uuid","ps":"remark"}'
        encoded = base64.b64encode(payload.encode()).decode()
        result = safe_b64_decode(encoded)
        assert result is not None
        assert '"add":"1.2.3.4"' in result
