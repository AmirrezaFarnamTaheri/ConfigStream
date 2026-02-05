# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for evasion features."""

import pytest
from configstream.intelligence.evasion import (
    rotate_tls_fingerprint,
    rotate_alpn,
    add_tls_fragmentation,
    add_multiplexing,
    enrich_outbound_with_evasion,
    preserve_sni_when_using_ip,
    TLSFingerprint,
)


class TestTLSFingerprintRotation:
    """Test TLS fingerprint rotation."""

    def test_rotate_tls_fingerprint_enabled(self):
        """Test fingerprint rotation when enabled."""
        result = rotate_tls_fingerprint("test-proxy-id", enabled=True)
        assert result is not None
        assert result["enabled"] is True
        assert "fingerprint" in result
        assert result["fingerprint"] in [fp.value for fp in TLSFingerprint]

    def test_rotate_tls_fingerprint_disabled(self):
        """Test fingerprint rotation when disabled."""
        result = rotate_tls_fingerprint("test-proxy-id", enabled=False)
        assert result is None

    def test_rotate_tls_fingerprint_specific(self):
        """Test specific fingerprint selection."""
        result = rotate_tls_fingerprint("test-proxy-id", enabled=True, fingerprint="chrome")
        assert result is not None
        assert result["fingerprint"] == "chrome"

    def test_rotate_tls_fingerprint_deterministic(self):
        """Test deterministic rotation based on proxy ID."""
        result1 = rotate_tls_fingerprint("same-id", enabled=True)
        result2 = rotate_tls_fingerprint("same-id", enabled=True)
        assert result1["fingerprint"] == result2["fingerprint"]


class TestALPNRotation:
    """Test ALPN rotation."""

    def test_rotate_alpn_enabled(self):
        """Test ALPN rotation when enabled."""
        result = rotate_alpn("test-proxy-id", enabled=True)
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0

    def test_rotate_alpn_disabled(self):
        """Test ALPN rotation when disabled."""
        result = rotate_alpn("test-proxy-id", enabled=False)
        assert result is None

    def test_rotate_alpn_specific(self):
        """Test specific ALPN selection."""
        result = rotate_alpn("test-proxy-id", enabled=True, alpn=["h2", "http/1.1"])
        assert result == ["h2", "http/1.1"]

    def test_rotate_alpn_deterministic(self):
        """Test deterministic rotation based on proxy ID."""
        result1 = rotate_alpn("same-id", enabled=True)
        result2 = rotate_alpn("same-id", enabled=True)
        assert result1 == result2


class TestTLSFragmentation:
    """Test TLS fragmentation."""

    def test_add_tls_fragmentation_enabled(self):
        """Test TLS fragmentation when enabled."""
        outbound = {
            "type": "vmess",
            "tls": {"enabled": True},
        }
        result = add_tls_fragmentation(outbound, enabled=True)
        assert "tls_fragment" in result["tls"]
        assert result["tls"]["tls_fragment"]["enabled"] is True
        assert "size" in result["tls"]["tls_fragment"]
        assert "sleep" in result["tls"]["tls_fragment"]

    def test_add_tls_fragmentation_disabled(self):
        """Test TLS fragmentation when disabled."""
        outbound = {"type": "vmess", "tls": {"enabled": True}}
        result = add_tls_fragmentation(outbound, enabled=False)
        assert "tls_fragment" not in result.get("tls", {})

    def test_add_tls_fragmentation_no_tls(self):
        """Test TLS fragmentation when TLS is not enabled."""
        outbound = {"type": "vmess"}
        result = add_tls_fragmentation(outbound, enabled=True)
        assert "tls_fragment" not in result.get("tls", {})


class TestMultiplexing:
    """Test multiplexing with padding."""

    def test_add_multiplexing_enabled(self):
        """Test multiplexing when enabled."""
        outbound = {"type": "vmess"}
        result = add_multiplexing(outbound, enabled=True)
        assert "multiplex" in result
        assert result["multiplex"]["enabled"] is True
        assert result["multiplex"]["padding"] is True

    def test_add_multiplexing_disabled(self):
        """Test multiplexing when disabled."""
        outbound = {"type": "vmess"}
        result = add_multiplexing(outbound, enabled=False)
        assert "multiplex" not in result

    def test_add_multiplexing_unsupported_protocol(self):
        """Test multiplexing with unsupported protocol."""
        outbound = {"type": "direct"}
        result = add_multiplexing(outbound, enabled=True)
        assert "multiplex" not in result


class TestEnrichOutbound:
    """Test outbound enrichment with evasion features."""

    def test_enrich_vmess_outbound(self):
        """Test enriching VMess outbound."""
        outbound = {
            "type": "vmess",
            "tls": {"enabled": True},
        }
        result = enrich_outbound_with_evasion(outbound, "test-id")
        assert "tls" in result
        if "utls" in result["tls"]:
            assert result["tls"]["utls"]["enabled"] is True

    def test_enrich_vless_outbound(self):
        """Test enriching VLESS outbound."""
        outbound = {
            "type": "vless",
            "tls": {"enabled": True},
        }
        result = enrich_outbound_with_evasion(outbound, "test-id")
        assert "tls" in result

    def test_enrich_trojan_outbound(self):
        """Test enriching Trojan outbound."""
        outbound = {
            "type": "trojan",
            "tls": {"enabled": True},
        }
        result = enrich_outbound_with_evasion(outbound, "test-id")
        assert "tls" in result

    def test_enrich_with_specific_fingerprint(self):
        """Test enriching with specific fingerprint."""
        outbound = {
            "type": "vmess",
            "tls": {"enabled": True},
        }
        result = enrich_outbound_with_evasion(
            outbound, "test-id", tls_fingerprint="firefox"
        )
        if "utls" in result.get("tls", {}):
            assert result["tls"]["utls"]["fingerprint"] == "firefox"


class TestSNIPreservation:
    """Test SNI/Host preservation when using IP."""

    def test_preserve_sni_with_hostname(self):
        """Test SNI preservation with original hostname."""
        outbound = {
            "type": "vmess",
            "server": "1.2.3.4",
            "tls": {"enabled": True},
        }
        result = preserve_sni_when_using_ip(outbound, "example.com")
        assert result["tls"]["server_name"] == "example.com"

    def test_preserve_host_websocket(self):
        """Test Host header preservation for WebSocket."""
        outbound = {
            "type": "vmess",
            "server": "1.2.3.4",
            "transport": {"type": "ws", "headers": {}},
        }
        result = preserve_sni_when_using_ip(outbound, "example.com")
        assert result["transport"]["headers"]["Host"] == "example.com"

    def test_preserve_host_http2(self):
        """Test Host preservation for HTTP/2."""
        outbound = {
            "type": "vmess",
            "server": "1.2.3.4",
            "transport": {"type": "http"},
        }
        result = preserve_sni_when_using_ip(outbound, "example.com")
        assert "example.com" in result["transport"]["host"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
