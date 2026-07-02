# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprehensive tests for SSR (ShadowsocksR) parser."""

import base64
import pytest
from configstream.parsers.ssr import parse_ssr


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


class TestSSRBasic:
    """Basic SSR parsing tests."""

    def test_valid_ssr(self):
        """Standard SSR config with all 6 colon-separated fields."""
        payload = "1.2.3.4:1234:auth_aes128_md5:aes-256-cfb:tls1.2_ticket_auth:Y2hhbGxlbmdl"
        config = f"ssr://{_b64(payload)}"
        proxy = parse_ssr(config)
        assert proxy is not None
        assert proxy.protocol == "ssr"
        assert proxy.address == "1.2.3.4"
        assert proxy.port == 1234
        assert proxy.details["protocol"] == "auth_aes128_md5"
        assert proxy.details["cipher"] == "aes-256-cfb"
        assert proxy.details["obfs"] == "tls1.2_ticket_auth"
        assert proxy.details["password"] == "challenge"

    def test_ssr_with_remarks(self):
        """SSR with remarks in query params."""
        password_b64 = _b64("mypassword")
        remarks_b64 = _b64("My Server")
        payload = f"10.0.0.1:443:origin:aes-128-gcm:plain:{password_b64}/?remarks={remarks_b64}"
        config = f"ssr://{_b64(payload)}"
        proxy = parse_ssr(config)
        assert proxy is not None
        assert proxy.remarks == "My Server"
        assert proxy.details["password"] == "mypassword"

    def test_ssr_with_obfsparam(self):
        """SSR with obfsparam and protoparam."""
        pw = _b64("pass")
        obfs_b64 = _b64("cloudflare.com")
        proto_b64 = _b64("1234")
        payload = f"host.tld:8080:auth_chain_a:chacha20:http:{pw}/?obfsparam={obfs_b64}&protoparam={proto_b64}"
        config = f"ssr://{_b64(payload)}"
        proxy = parse_ssr(config)
        assert proxy is not None
        assert proxy.details["params"]["obfsparam"] == "cloudflare.com"
        assert proxy.details["params"]["protoparam"] == "1234"

    def test_ssr_no_scheme_returns_none(self):
        """Config without ssr:// prefix should return None."""
        assert parse_ssr("http://example.com") is None

    def test_ssr_empty_config_returns_none(self):
        """Empty string should return None."""
        assert parse_ssr("") is None


class TestSSREdgeCases:
    """Edge cases for SSR parser."""

    def test_ssr_invalid_payload_too_short(self):
        """Payload with fewer than 6 colon-separated parts."""
        payload = _b64("1.2.3.4:1234:auth")
        config = f"ssr://{payload}"
        assert parse_ssr(config) is None

    def test_ssr_invalid_port_non_numeric(self):
        """Non-numeric port should be rejected."""
        payload = _b64("host:abc:origin:none:plain:password")
        config = f"ssr://{payload}"
        assert parse_ssr(config) is None

    def test_ssr_port_out_of_range(self):
        """Port outside 1-65535 should be rejected."""
        payload = _b64("host:0:origin:none:plain:password")
        config = f"ssr://{payload}"
        assert parse_ssr(config) is None

    def test_ssr_port_65535_valid(self):
        """Port 65535 should be accepted (upper bound)."""
        payload = _b64("host:65535:origin:none:plain:password")
        config = f"ssr://{payload}"
        proxy = parse_ssr(config)
        assert proxy is not None
        assert proxy.port == 65535

    def test_ssr_long_server_name(self):
        """Server name > 255 chars should be rejected."""
        payload = _b64(f"{'a'*256}:443:origin:none:plain:password")
        config = f"ssr://{payload}"
        assert parse_ssr(config) is None

    def test_ssr_excessively_long_payload(self):
        """Payload > 4096 chars after ssr:// should be rejected."""
        long_payload = _b64("x" * 5000)
        config = f"ssr://{long_payload}"
        assert parse_ssr(config) is None

    def test_ssr_password_fallback_raw(self):
        """If password is not valid base64, fall back to raw value.
        Note: The entire payload is base64-encoded first, then decoded by the parser.
        'rawpassword' is a valid base64 string (decodes to '??'), so use a string
        that is NOT valid base64 to test the fallback.
        """
        # Use a payload where the password part is clearly not base64
        # We encode the whole thing, then the parser decodes and splits
        payload = "host:443:origin:none:plain:!!!notbase64!!!"
        config = f"ssr://{_b64(payload)}"
        proxy = parse_ssr(config)
        assert proxy is not None
        # The password will be the raw text after base64 decode of the full payload
        assert proxy.details["password"] == "!!!notbase64!!!"

    def test_ssr_blank_remarks(self):
        """Blank remarks should result in empty string."""
        pw = _b64("pass")
        payload = f"host:443:origin:none:plain:{pw}/?remarks="
        config = f"ssr://{_b64(payload)}"
        proxy = parse_ssr(config)
        assert proxy is not None
        assert proxy.remarks == ""


class TestSSRRealWorld:
    """Real-world SSR config patterns."""

    def test_ssr_typical_subscription_format(self):
        """Typical SSR subscription entry format."""
        params = (
            "remarks=SGVsbG8="
            "&group=VGVzdA=="
            "&obfsparam=d3d3Lmdvb2dsZS5jb20="
            "&protoparam="
        )
        pw = _b64("secret123")
        payload = f"sg.example.com:12345:auth_aes128_sha1:aes-256-cfb:http:{pw}/?{params}"
        config = f"ssr://{_b64(payload)}"
        proxy = parse_ssr(config)
        assert proxy is not None
        assert proxy.address == "sg.example.com"
        assert proxy.port == 12345
        assert proxy.remarks == "Hello"

    def test_ssr_ipv4_address(self):
        """IPv4 address in SSR."""
        pw = _b64("pass")
        payload = f"192.168.1.1:8080:origin:none:plain:{pw}"
        config = f"ssr://{_b64(payload)}"
        proxy = parse_ssr(config)
        assert proxy is not None
        assert proxy.address == "192.168.1.1"
