import pytest
from configstream.parsers import (
    _parse_ss,
    _parse_ssr,
    _parse_vmess,
    _parse_vless,
    _parse_trojan,
    _safe_b64_decode,
    _extract_config_lines,
    _is_plausible_proxy_config,
)


class TestParsersExtended:
    def test_parse_ss_sip002_edge_cases(self):
        # Invalid base64
        assert _parse_ss("ss://invalid-b64#remark") is None
        # Missing colon in user info
        assert _parse_ss("ss://YWVzLTI1Ni1nY20cGFzc3dvcmRAMjA0LjE1Mi4yMTUuMTE5OjgwODA=#remark") is None
        # Missing port
        assert _parse_ss("ss://YWVzLTI1Ni1nY206cGFzc3dvcmRAMjA0LjE1Mi4yMTUuMTE5#remark") is None
        # Invalid port
        assert _parse_ss("ss://YWVzLTI1Ni1nY206cGFzc3dvcmRAMjA0LjE1Mi4yMTUuMTE5OjcwMDAw#remark") is None

    def test_parse_ssr_invalid(self):
        # Invalid base64
        assert _parse_ssr("ssr://invalid-b64") is None
        # Not enough parts
        assert _parse_ssr("ssr://c2VydmVyOnBvcnQ6cHJvdG86Y2lwaGVyOm9iZnM") is None
        # Invalid port
        assert _parse_ssr("ssr://c2VydmVyOjcwMDAwOnByb3RvOmNpcGhlcjpvYmZzOnBhc3N3b3Jk") is None

    def test_parse_vmess_invalid(self):
        # Invalid base64
        assert _parse_vmess("vmess://invalid-b64") is None
        # Missing required keys
        assert _parse_vmess("vmess://eyJhZGQiOiJleGFtcGxlLmNvbSIsImlkIjoiMTIzIn0=") is None  # Missing port
        # Invalid port
        assert _parse_vmess("vmess://eyJhZGQiOiJleGFtcGxlLmNvbSIsInBvcnQiOjcwMDAwLCJpZCI6IjEyMyJ9") is None

    def test_parse_vless_invalid(self):
        # Missing hostname
        assert _parse_vless("vless://123@:443#remark") is None
        # Invalid port
        assert _parse_vless("vless://123@example.com:70000#remark") is None

    def test_parse_trojan_invalid(self):
        # Missing hostname
        assert _parse_trojan("trojan://123@:443#remark") is None
        # Invalid port
        assert _parse_trojan("trojan://123@example.com:70000#remark") is None

    def test_safe_b64_decode_invalid_chars(self):
        assert _safe_b64_decode("aGVsbG8^d29ybGQ=") == "aGVsbG8^d29ybGQ="

    def test_safe_b64_decode_oversized_input(self):
        oversized_input = "a" * 20000
        assert _safe_b64_decode(oversized_input) == oversized_input

    def test_safe_b64_decode_non_utf8(self):
        non_utf8_b64 = "g/yA"  # Corresponds to non-UTF8 bytes
        assert _safe_b64_decode(non_utf8_b64) == non_utf8_b64

    def test_extract_config_lines_oversized(self):
        from configstream.constants import MAX_LINES_PER_SOURCE
        lines = ["http://a.com"] * (MAX_LINES_PER_SOURCE + 1)
        payload = "\n".join(lines)
        assert len(_extract_config_lines(payload)) == MAX_LINES_PER_SOURCE

    def test_extract_config_lines_empty_and_comments(self):
        payload = """
# comment
http://a.com

http://b.com
"""
        assert len(_extract_config_lines(payload)) == 2

    def test_is_plausible_proxy_config(self):
        assert _is_plausible_proxy_config("http://example.com:8080")
        assert not _is_plausible_proxy_config("not-a-proxy")
        assert not _is_plausible_proxy_config("http://")
        assert _is_plausible_proxy_config("ssh://user@host")
