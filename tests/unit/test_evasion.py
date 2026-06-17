# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for evasion intelligence module."""

from configstream.intelligence.evasion import (
    rotate_tls_fingerprint,
    rotate_alpn,
    add_multiplexing,
    enrich_outbound_with_evasion,
    preserve_sni_when_using_ip,
)


class TestTLSFingerprintRotation:
    def test_rotate_tls_fingerprint_enabled(self):
        """Test TLS fingerprint rotation when enabled."""
        result = rotate_tls_fingerprint("test_proxy", enabled=True)
        assert result is not None
        assert result["enabled"] is True
        assert "fingerprint" in result

    def test_rotate_tls_fingerprint_disabled(self):
        """Test TLS fingerprint rotation when disabled."""
        result = rotate_tls_fingerprint("test_proxy", enabled=False)
        assert result is None

    def test_rotate_tls_fingerprint_specific(self):
        """Test TLS fingerprint rotation with specific fingerprint."""
        result = rotate_tls_fingerprint(
            "test_proxy", enabled=True, fingerprint="chrome"
        )
        assert result is not None
        assert result["fingerprint"] == "chrome"

    def test_rotate_tls_fingerprint_deterministic(self):
        """Test that rotation is deterministic based on proxy ID."""
        result1 = rotate_tls_fingerprint("proxy1", enabled=True)
        result2 = rotate_tls_fingerprint("proxy1", enabled=True)
        assert result1["fingerprint"] == result2["fingerprint"]


class TestALPNRotation:
    def test_rotate_alpn_enabled(self):
        """Test ALPN rotation when enabled."""
        result = rotate_alpn("test_proxy", enabled=True)
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0

    def test_rotate_alpn_disabled(self):
        """Test ALPN rotation when disabled."""
        result = rotate_alpn("test_proxy", enabled=False)
        assert result is None

    def test_rotate_alpn_specific(self):
        """Test ALPN rotation with specific list."""
        specific = ["h2", "http/1.1"]
        result = rotate_alpn("test_proxy", enabled=True, alpn=specific)
        assert result == specific

    def test_rotate_alpn_deterministic(self):
        """Test that ALPN rotation is deterministic."""
        result1 = rotate_alpn("proxy1", enabled=True)
        result2 = rotate_alpn("proxy1", enabled=True)
        assert result1 == result2


class TestMultiplexing:
    def test_add_multiplexing_enabled(self):
        """Test multiplexing when enabled."""
        outbound = {"type": "vmess"}
        result = add_multiplexing(outbound, enabled=True)
        assert "multiplex" in result
        assert result["multiplex"]["enabled"] is True
        assert result["multiplex"]["protocol"] == "h2mux"

    def test_add_multiplexing_disabled(self):
        """Test multiplexing when disabled."""
        outbound = {"type": "vmess"}
        result = add_multiplexing(outbound, enabled=False)
        assert "multiplex" not in result

    def test_add_multiplexing_unsupported_protocol(self):
        """Test multiplexing on unsupported protocol."""
        outbound = {"type": "wireguard"}
        result = add_multiplexing(outbound, enabled=True)
        assert "multiplex" not in result


class TestEnrichOutbound:
    def test_enrich_vmess_outbound(self):
        """Test enriching a VMess outbound."""
        outbound = {
            "type": "vmess",
            "tls": {"enabled": True},
        }
        result = enrich_outbound_with_evasion(
            outbound,
            "test_proxy",
            enable_utls=True,
            enable_alpn=True,
            enable_fragmentation=True,
        )
        assert "utls" in result["tls"]
        assert "alpn" in result["tls"]
        # Fragmentation is disabled/no-op on TLS object, but added on dial
        assert "tls_fragment" not in result["tls"]
        assert "dial" in result
        assert result["dial"]["fragment"]["enabled"] is True
        assert "length" in result["dial"]["fragment"]
        assert "multiplex" in result

    def test_enrich_vless_outbound(self):
        """Test enriching a VLESS outbound."""
        outbound = {
            "type": "vless",
            "tls": {"enabled": True},
        }
        result = enrich_outbound_with_evasion(outbound, "test_proxy")
        assert "utls" in result["tls"]

    def test_enrich_trojan_outbound(self):
        """Test enriching a Trojan outbound."""
        outbound = {
            "type": "trojan",
            "tls": {"enabled": True},
        }
        result = enrich_outbound_with_evasion(outbound, "test_proxy")
        assert "utls" in result["tls"]

    def test_enrich_with_specific_fingerprint(self):
        """Test enriching with a specific fingerprint."""
        outbound = {
            "type": "vmess",
            "tls": {"enabled": True},
        }
        result = enrich_outbound_with_evasion(
            outbound, "test_proxy", tls_fingerprint="randomized"
        )
        assert result["tls"]["utls"]["fingerprint"] == "randomized"

    def test_enrich_fragmentation_presets(self):
        """Test fragmentation presets selection and disable capability."""
        # 1. Test disabled
        outbound = {
            "type": "vless",
            "tls": {"enabled": True},
        }
        res_disabled = enrich_outbound_with_evasion(
            outbound, "test_proxy", enable_fragmentation=False
        )
        assert "dial" not in res_disabled or "fragment" not in res_disabled.get(
            "dial", {}
        )

        # 2. Test specific preset (light)
        res_light = enrich_outbound_with_evasion(
            outbound, "test_proxy", enable_fragmentation=True, fragment_preset="light"
        )
        assert res_light["dial"]["fragment"]["enabled"] is True
        assert res_light["dial"]["fragment"]["packets"] == "tlshello"
        assert res_light["dial"]["fragment"]["length"] == "100-200"
        assert res_light["dial"]["fragment"]["interval"] == "10-20"

        # 3. Test Reality is skipped
        outbound_reality = {
            "type": "vless",
            "tls": {
                "enabled": True,
                "reality": {"enabled": True, "public_key": "some_key"},
            },
        }
        res_reality = enrich_outbound_with_evasion(
            outbound_reality, "test_proxy", enable_fragmentation=True
        )
        assert "dial" not in res_reality or "fragment" not in res_reality.get(
            "dial", {}
        )

    def test_enrich_tfo_and_mptcp(self):
        """Test enabling TCP Fast Open and Multipath TCP."""
        outbound = {"type": "vmess"}
        result = enrich_outbound_with_evasion(
            outbound, "test_proxy", enable_tfo=True, enable_mptcp=True
        )
        assert "dial" in result
        assert result["dial"]["tcp_fast_open"] is True
        assert result["dial"]["tcp_multi_path"] is True

    def test_enrich_padding(self):
        """Test enabling TLS padding."""
        outbound = {
            "type": "vmess",
            "tls": {"enabled": True},
        }
        result = enrich_outbound_with_evasion(
            outbound, "test_proxy", enable_padding=True
        )
        assert "tls" in result
        assert result["tls"]["padding"] is True

    def test_enrich_ech(self):
        """Test enabling ECH."""
        outbound = {
            "type": "vless",
            "tls": {"enabled": True},
        }
        result = enrich_outbound_with_evasion(
            outbound, "test_proxy", ech_config="test_ech_config"
        )
        assert "tls" in result
        assert result["tls"]["ech"]["enabled"] is True
        assert result["tls"]["ech"]["config"] == "test_ech_config"


class TestSNIPreservation:
    def test_preserve_sni_with_hostname(self):
        """Test SNI preservation with hostname."""
        outbound = {
            "type": "vmess",
            "tls": {"enabled": True},
        }
        result = preserve_sni_when_using_ip(outbound, "example.com")
        assert result["tls"]["server_name"] == "example.com"

    def test_preserve_host_websocket(self):
        """Test Host preservation for WebSocket."""
        outbound = {
            "type": "vmess",
            "transport": {"type": "ws", "headers": {}},
        }
        result = preserve_sni_when_using_ip(outbound, "example.com")
        assert result["transport"]["headers"]["Host"] == "example.com"

    def test_preserve_host_http2(self):
        """Test Host preservation for HTTP/2."""
        outbound = {
            "type": "vmess",
            "transport": {"type": "http"},
        }
        result = preserve_sni_when_using_ip(outbound, "example.com")
        assert result["transport"]["host"] == ["example.com"]
