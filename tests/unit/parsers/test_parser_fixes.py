# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for parser fixes applied during the 2026-02-08 audit.
Covers: Shadowsocks password drop, Trojan password fallback,
PipelineStats sync to_dict, and signer input validation.
"""

import pytest
from configstream.parsers.shadowsocks import parse_ss
from configstream.parsers.trojan import parse_trojan
from configstream.pipeline_stats import PipelineStats
from configstream.signer import Signer
import inspect
import threading

# ---------------------------------------------------------------------------
# Shadowsocks: Password drop after failed fallback
# ---------------------------------------------------------------------------


class TestShadowsocksPasswordDrop:
    """Tests for the password drop logic in parse_ss."""

    def test_ss_with_valid_password(self):
        """Normal SS config with valid method:password should parse."""
        # aes-256-gcm:testpassword base64 -> YWVzLTI1Ni1nY206dGVzdHBhc3N3b3Jk
        config = "ss://YWVzLTI1Ni1nY206dGVzdHBhc3N3b3Jk@1.2.3.4:8388#test"
        proxy = parse_ss(config)
        assert proxy is not None
        assert proxy.protocol in ("ss", "shadowsocks")
        assert proxy.address == "1.2.3.4"
        assert proxy.port == 8388

    def test_ss_empty_password_no_fallback_returns_none(self):
        """SS config with method: (empty password) and no fallback should be dropped."""
        # aes-256-gcm: (note the colon but no password) -> YWVzLTI1Ni1nY206
        import base64

        encoded = base64.urlsafe_b64encode(b"aes-256-gcm:").decode().rstrip("=")
        config = f"ss://{encoded}@1.2.3.4:8388#test"
        proxy = parse_ss(config)
        assert proxy is None, "Should drop SS proxy with empty password and no fallback"

    def test_ss_empty_password_with_query_fallback(self):
        """SS config with empty password but valid password in query params should parse."""
        import base64

        encoded = base64.urlsafe_b64encode(b"aes-256-gcm:").decode().rstrip("=")
        config = f"ss://{encoded}@1.2.3.4:8388/?password=secretpass#test"
        proxy = parse_ss(config)
        assert proxy is not None
        assert proxy.address == "1.2.3.4"
        assert proxy.details["password"] == "secretpass"

    def test_ss_valid_password_parses_normally(self):
        """SS config with valid method:password should not trigger the drop."""
        import base64

        encoded = (
            base64.urlsafe_b64encode(b"chacha20-ietf-poly1305:mysecretpw")
            .decode()
            .rstrip("=")
        )
        config = f"ss://{encoded}@10.0.0.1:443#myserver"
        proxy = parse_ss(config)
        assert proxy is not None
        assert proxy.port == 443


# ---------------------------------------------------------------------------
# Trojan: parsed.password fallback
# ---------------------------------------------------------------------------


class TestTrojanPasswordFallback:
    """Tests for the Trojan parsed.password fallback."""

    def test_trojan_with_username(self):
        """Normal trojan with username (password) should parse."""
        config = "trojan://mypassword@server.example.com:443#TestNode"
        proxy = parse_trojan(config)
        assert proxy is not None
        assert proxy.uuid == "mypassword"
        assert proxy.protocol == "trojan"

    def test_trojan_no_credentials_returns_none(self):
        """Trojan with no username, no password, no query params should drop."""
        config = "trojan://@server.example.com:443#TestNode"
        proxy = parse_trojan(config)
        assert proxy is None, "Trojan with empty credentials should be dropped"

    def test_trojan_with_query_param_fallback(self):
        """Trojan with password in query params should use it as fallback."""
        config = "trojan://@server.example.com:443?password=fallbackpw#TestNode"
        proxy = parse_trojan(config)
        if proxy is not None:
            assert proxy.uuid == "fallbackpw"


# ---------------------------------------------------------------------------
# PipelineStats: to_dict() is synchronous
# ---------------------------------------------------------------------------


class TestPipelineStatsSync:
    """Tests that PipelineStats.to_dict() is synchronous."""

    def test_to_dict_is_not_async(self):
        """to_dict must be a regular function, not a coroutine."""
        stats = PipelineStats()
        assert not inspect.iscoroutinefunction(
            stats.to_dict
        ), "to_dict must be synchronous (not async) to avoid coroutine-without-await bugs"

    def test_to_dict_returns_dict_directly(self):
        """to_dict should return a dict, not a coroutine object."""
        stats = PipelineStats()
        result = stats.to_dict()
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

    def test_to_dict_includes_timestamps(self):
        """to_dict should include start_time and end_time."""
        stats = PipelineStats()
        d = stats.to_dict()
        assert "start_time" in d
        assert "end_time" in d
        # start_time should be an ISO string
        assert isinstance(d["start_time"], str)
        assert d["end_time"] is None  # Not set yet

    def test_to_dict_thread_safe(self):
        """to_dict should be safe to call from multiple threads."""
        stats = PipelineStats()
        results = []
        errors = []

        def call_to_dict():
            try:
                d = stats.to_dict()
                results.append(d)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=call_to_dict) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread-safety errors: {errors}"
        assert len(results) == 10

    def test_get_snapshot_is_not_async(self):
        """get_snapshot must also be synchronous."""
        stats = PipelineStats()
        assert not inspect.iscoroutinefunction(stats.get_snapshot)
        result = stats.get_snapshot()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Signer: Input validation
# ---------------------------------------------------------------------------


class TestSignerInputValidation:
    """Tests for Signer input validation."""

    def test_signer_rejects_odd_length_hex(self):
        """Odd-length hex string should raise ValueError."""
        with pytest.raises(ValueError, match="even length"):
            Signer(private_key_hex="abc")

    def test_signer_rejects_wrong_length_key(self):
        """Key that's not 32 or 64 bytes should raise ValueError."""
        # 16 bytes = 32 hex chars
        short_key = "00" * 16
        with pytest.raises(ValueError, match="32 or 64 bytes"):
            Signer(private_key_hex=short_key)

    def test_signer_accepts_32_byte_key(self):
        """32-byte key should be accepted."""
        key_32 = "00" * 32
        signer = Signer(private_key_hex=key_32)
        assert signer._private_key is not None

    def test_signer_accepts_64_byte_key(self):
        """64-byte key (seed + pub) should be accepted, using first 32 bytes."""
        key_64 = "00" * 64
        signer = Signer(private_key_hex=key_64)
        assert signer._private_key is not None

    def test_signer_no_key_creates_empty_signer(self):
        """No key should create a signer that cannot sign."""
        signer = Signer(private_key_hex=None)
        assert signer._private_key is None
        with pytest.raises(ValueError, match="not configured"):
            signer.sign_subscription("test content")
