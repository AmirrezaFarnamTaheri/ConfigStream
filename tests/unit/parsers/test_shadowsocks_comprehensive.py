# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprehensive tests for Shadowsocks parser beyond basic decoding."""

import base64
from configstream.parsers.shadowsocks import parse_ss, parse_ss2022


def _ss_encode(method_password):
    """Encode method:password to base64 without padding."""
    return base64.urlsafe_b64encode(method_password.encode()).decode().rstrip("=")


class TestSSPluginSupport:
    """Shadowsocks with SIP003 plugins."""

    def test_ss_with_plugin(self):
        """SS with simple-obfs plugin."""
        encoded = _ss_encode("aes-256-gcm:password")
        config = f"ss://{encoded}@1.2.3.4:8388?plugin=obfs-local;obfs=http;obfs-host=example.com#Plugin"
        proxy = parse_ss(config)
        assert proxy is not None
        assert proxy.details.get("plugin") == "obfs-local"
        assert "obfs-host" in proxy.details.get("plugin_opts", "")

    def test_ss_with_v2ray_plugin(self):
        """SS with v2ray-plugin."""
        encoded = _ss_encode("chacha20-ietf-poly1305:pass")
        config = (
            f"ss://{encoded}@host:443?plugin=v2ray-plugin;tls;host=example.com;path=/ws"
        )
        proxy = parse_ss(config)
        assert proxy is not None
        assert "v2ray-plugin" in proxy.details.get("plugin", "")


class TestSS2022:
    """Shadowsocks 2022 parser tests."""

    def test_ss2022_basic(self):
        """Basic Shadowsocks 2022 config."""
        encoded = _ss_encode("2022-blake3-aes-256-gcm:base64key==")
        config = f"ss2022://{encoded}@host:443#SS2022"
        proxy = parse_ss2022(config)
        assert proxy is not None
        assert proxy.protocol == "ss2022"
        assert proxy.config.startswith("ss2022://")

    def test_ss2022_no_scheme(self):
        """Config without ss2022:// should return None."""
        assert parse_ss2022("ss://something") is None


class TestSSPortValidation:
    """Port validation edge cases."""

    def test_valid_port_range(self):
        """Ports in valid range should work."""
        encoded = _ss_encode("aes-256-gcm:pass")
        assert parse_ss(f"ss://{encoded}@host:1") is not None
        assert parse_ss(f"ss://{encoded}@host:65535") is not None

    def test_invalid_port_zero(self):
        """Port 0 should be rejected."""
        encoded = _ss_encode("aes-256-gcm:pass")
        assert parse_ss(f"ss://{encoded}@host:0") is None

    def test_invalid_port_negative(self):
        """Negative port should be rejected (won't parse as int)."""
        assert parse_ss("ss://YWVzLTI1Ni1nY206cGFzcw==@host:-1") is None


class TestSSMethodValidation:
    """SS method validation."""

    def test_invalid_method_name(self):
        """Invalid short method name should be rejected."""
        encoded = _ss_encode("ss:pass")
        assert parse_ss(f"ss://{encoded}@host:443") is None

    def test_null_method(self):
        """'null' method should be rejected."""
        encoded = _ss_encode("null:pass")
        assert parse_ss(f"ss://{encoded}@host:443") is None

    def test_empty_method(self):
        """Empty method should be rejected."""
        encoded = _ss_encode(":pass")
        assert parse_ss(f"ss://{encoded}@host:443") is None


class TestSSClassicFormat:
    """Classic SIP002 format without @."""

    def test_classic_format(self):
        """Classic format: base64(method:password:host:port)."""
        import base64

        payload = (
            base64.b64encode(b"aes-256-gcm:password:1.2.3.4:8388").decode().rstrip("=")
        )
        config = f"ss://{payload}#test"
        proxy = parse_ss(config)
        assert proxy is not None
        assert proxy.address == "1.2.3.4"
        assert proxy.port == 8388

    def test_classic_format_too_few_parts(self):
        """Classic format with only 3 parts should fail."""
        import base64

        payload = base64.b64encode(b"method:pass:host").decode().rstrip("=")
        config = f"ss://{payload}"
        assert parse_ss(config) is None


class TestSSPasswordFallback:
    """Password fallback mechanisms."""

    def test_password_in_query(self):
        """Password from query params when user_info is empty."""
        encoded = _ss_encode("aes-256-gcm:")
        config = f"ss://{encoded}@host:443?password=querypass#test"
        proxy = parse_ss(config)
        assert proxy is not None
        assert proxy.details.get("password") == "querypass"

    def test_password_psk_fallback(self):
        """Password from 'psk' query param."""
        encoded = _ss_encode("chacha20-ietf-poly1305:")
        config = f"ss://{encoded}@host:443?psk=pskpass"
        proxy = parse_ss(config)
        assert proxy is not None
        assert proxy.details.get("password") == "pskpass"
