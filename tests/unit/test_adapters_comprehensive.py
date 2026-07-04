# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for adapters.py module.
Tests all adapter classes with edge cases and error handling.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from configstream.adapters import (
    SurgeAdapter,
    LoonAdapter,
    QuantumultXAdapter,
    SIP008Adapter,
    ShadowrocketAdapter,
    get_adapter,
)
from configstream.models import Proxy


class TestSurgeAdapter:
    """Comprehensive tests for SurgeAdapter."""

    def test_shadowsocks_export(self):
        """Test exporting Shadowsocks proxy."""
        adapter = SurgeAdapter()
        proxy = Proxy(
            config="ss://test",
            protocol="ss",
            address="1.2.3.4",
            port=443,
            details={"method": "chacha20-ietf-poly1305", "password": "secret"},
            remarks="SS Proxy",
        )
        result = adapter.export([proxy])

        assert "SS Proxy = ss, 1.2.3.4, 443" in result
        assert "encrypt-method=chacha20-ietf-poly1305" in result
        assert "password=secret" in result

    def test_vmess_export(self):
        """Test exporting VMess proxy."""
        adapter = SurgeAdapter()
        proxy = Proxy(
            config="vmess://test",
            protocol="vmess",
            address="example.com",
            port=443,
            uuid="12345678-1234-1234-1234-123456789012",
        )
        result = adapter.export([proxy])

        assert "vmess, example.com, 443" in result
        assert "username=12345678-1234-1234-1234-123456789012" in result

    def test_trojan_export(self):
        """Test exporting Trojan proxy."""
        adapter = SurgeAdapter()
        proxy = Proxy(
            config="trojan://test",
            protocol="trojan",
            address="trojan.example.com",
            port=443,
            uuid="mypassword",
        )
        result = adapter.export([proxy])

        assert "trojan, trojan.example.com, 443" in result
        assert "password=mypassword" in result

    def test_http_proxy_with_auth(self):
        """Test exporting HTTP proxy with authentication."""
        adapter = SurgeAdapter()
        proxy = Proxy(
            config="http://test",
            protocol="http",
            address="proxy.example.com",
            port=8080,
            uuid="user123",
            details={"password": "pass123"},
        )
        result = adapter.export([proxy])

        assert "http, proxy.example.com, 8080" in result
        assert "username=user123" in result
        assert "password=pass123" in result

    def test_http_proxy_without_auth(self):
        """Test exporting HTTP proxy without authentication."""
        adapter = SurgeAdapter()
        proxy = Proxy(
            config="http://test",
            protocol="http",
            address="proxy.example.com",
            port=8080,
        )
        result = adapter.export([proxy])

        assert "http, proxy.example.com, 8080" in result
        # No auth parameters
        assert "username" not in result or "username=," not in result

    def test_socks5_export(self):
        """Test exporting SOCKS5 proxy."""
        adapter = SurgeAdapter()
        proxy = Proxy(
            config="socks5://test",
            protocol="socks5",
            address="socks.example.com",
            port=1080,
            uuid="sockuser",
            details={"password": "sockpass"},
        )
        result = adapter.export([proxy])

        assert "socks5, socks.example.com, 1080" in result
        assert "username=sockuser" in result
        assert "password=sockpass" in result

    def test_snell_export(self):
        """Test exporting Snell proxy."""
        adapter = SurgeAdapter()
        proxy = Proxy(
            config="snell://test",
            protocol="snell",
            address="snell.example.com",
            port=8388,
            details={"psk": "presharedkey123"},
        )
        result = adapter.export([proxy])

        assert "snell, snell.example.com, 8388" in result
        assert "psk=presharedkey123" in result

    def test_unsupported_protocol(self):
        """Test exporting unsupported protocol returns empty string."""
        adapter = SurgeAdapter()
        proxy = Proxy(
            config="unknown://test", protocol="unknown", address="test.com", port=443
        )
        result = adapter.export([proxy])

        # Should contain header but not the proxy
        assert "# Surge Policy Export" in result

    def test_proxy_name_with_commas_replaced(self):
        """Test that commas in proxy names are replaced."""
        adapter = SurgeAdapter()
        proxy = Proxy(
            config="ss://test",
            protocol="ss",
            address="1.2.3.4",
            port=443,
            details={"method": "aes-256-gcm", "password": "pass"},
            remarks="Test, Proxy, Name",
        )
        result = adapter.export([proxy])

        assert "Test_ Proxy_ Name" in result
        assert "Test, Proxy, Name" not in result

    def test_export_with_washed_outbounds(self):
        """Test exporting with washed outbounds."""
        adapter = SurgeAdapter()
        proxy = Proxy(
            config="ss://test",
            protocol="ss",
            address="1.2.3.4",
            port=443,
            details={"method": "aes-256-gcm", "password": "pass"},
        )

        washed_outbounds = [
            {"type": "wireguard", "tag": "🛡️ Secure-US-1", "detour": "RELAY-test"}
        ]

        with patch(
            "configstream.adapters.surge.format_singbox_chain_for_surge"
        ) as mock_format:
            mock_format.return_value = "WireGuard chain config"
            result = adapter.export([proxy], washed_outbounds)

            assert "WireGuard chain config" in result

    def test_export_exception_handling(self):
        """Test that exceptions during export are handled gracefully."""
        adapter = SurgeAdapter()
        # Create a proxy that might cause issues
        proxy = Mock(spec=Proxy)
        proxy.protocol = "ss"
        proxy.address = "1.2.3.4"
        proxy.port = 443
        proxy.remarks = None
        # Use MagicMock for details to allow mocking get method
        proxy.details = MagicMock()
        # Make accessing details raise an exception
        proxy.details.get.side_effect = Exception("Test error")

        result = adapter.export([proxy])

        # Should not crash, should return header
        assert "# Surge Policy Export" in result


class TestLoonAdapter:
    """Comprehensive tests for LoonAdapter."""

    def test_shadowsocks_export(self):
        """Test Loon format for Shadowsocks."""
        adapter = LoonAdapter()
        proxy = Proxy(
            config="ss://test",
            protocol="shadowsocks",
            address="1.2.3.4",
            port=443,
            details={"method": "aes-256-gcm", "password": "secret"},
            remarks="Loon SS",
        )
        result = adapter.export([proxy])

        assert 'Loon SS = shadowsocks, 1.2.3.4, 443, aes-256-gcm, "secret"' in result

    def test_vmess_export(self):
        """Test Loon format for VMess."""
        adapter = LoonAdapter()
        proxy = Proxy(
            config="vmess://test",
            protocol="vmess",
            address="example.com",
            port=443,
            uuid="test-uuid",
            details={"method": "auto"},
        )
        result = adapter.export([proxy])

        assert 'vmess, example.com, 443, auto, "test-uuid"' in result

    def test_trojan_export(self):
        """Test Loon format for Trojan."""
        adapter = LoonAdapter()
        proxy = Proxy(
            config="trojan://test",
            protocol="trojan",
            address="trojan.com",
            port=443,
            uuid="password123",
        )
        result = adapter.export([proxy])

        assert 'trojan, trojan.com, 443, "password123"' in result

    def test_name_sanitization(self):
        """Test that '=' and ',' are replaced in names."""
        adapter = LoonAdapter()
        proxy = Proxy(
            config="ss://test",
            protocol="shadowsocks",
            address="1.2.3.4",
            port=443,
            details={"method": "aes-256-gcm", "password": "pass"},
            remarks="Test=Proxy,Name",
        )
        result = adapter.export([proxy])

        assert "Test_Proxy_Name" in result

    def test_unsupported_protocol(self):
        """Test unsupported protocol returns empty."""
        adapter = LoonAdapter()
        proxy = Proxy(
            config="unknown://test", protocol="unknown", address="test.com", port=443
        )
        result = adapter.export([proxy])

        assert "# Loon Proxy Export" in result


class TestQuantumultXAdapter:
    """Comprehensive tests for QuantumultXAdapter."""

    def test_shadowsocks_export(self):
        """Test QuantumultX format for Shadowsocks."""
        adapter = QuantumultXAdapter()
        proxy = Proxy(
            config="ss://test",
            protocol="shadowsocks",
            address="1.2.3.4",
            port=443,
            details={"method": "aes-256-gcm", "password": "secret"},
            remarks="QX SS",
        )
        result = adapter.export([proxy])

        assert "shadowsocks=QX SS: 1.2.3.4, 443" in result
        assert "method=aes-256-gcm" in result
        assert "password=secret" in result

    def test_vmess_export(self):
        """Test QuantumultX format for VMess."""
        adapter = QuantumultXAdapter()
        proxy = Proxy(
            config="vmess://test",
            protocol="vmess",
            address="example.com",
            port=443,
            uuid="test-uuid",
        )
        result = adapter.export([proxy])

        assert "vmess=vmess_example.com: example.com, 443" in result

    def test_trojan_export(self):
        """Test QuantumultX format for Trojan."""
        adapter = QuantumultXAdapter()
        proxy = Proxy(
            config="trojan://test",
            protocol="trojan",
            address="trojan.com",
            port=443,
            uuid="password123",
        )
        result = adapter.export([proxy])

        assert "trojan=trojan_trojan.com: trojan.com, 443" in result
        assert "password=password123" in result


class TestSIP008Adapter:
    """Comprehensive tests for SIP008Adapter."""

    def test_shadowsocks_export(self):
        """Test SIP008 JSON format for Shadowsocks."""
        adapter = SIP008Adapter()
        proxy = Proxy(
            config="ss://test",
            protocol="shadowsocks",
            address="1.2.3.4",
            port=443,
            details={"method": "aes-256-gcm", "password": "secret"},
            remarks="SIP008 SS",
        )
        result = adapter.export([proxy])

        data = json.loads(result)
        assert data["version"] == 1
        assert len(data["servers"]) == 1
        assert data["servers"][0]["server"] == "1.2.3.4"
        assert data["servers"][0]["server_port"] == 443
        assert data["servers"][0]["password"] == "secret"
        assert data["servers"][0]["method"] == "aes-256-gcm"
        assert data["servers"][0]["remarks"] == "SIP008 SS"

    def test_non_shadowsocks_ignored(self):
        """Test that non-Shadowsocks proxies are ignored."""
        adapter = SIP008Adapter()
        proxy1 = Proxy(
            config="vmess://test",
            protocol="vmess",
            address="example.com",
            port=443,
            uuid="test",
        )
        proxy2 = Proxy(
            config="ss://test",
            protocol="shadowsocks",
            address="1.2.3.4",
            port=443,
            details={"method": "aes-256-gcm", "password": "secret"},
        )
        result = adapter.export([proxy1, proxy2])

        data = json.loads(result)
        # Only SS proxy should be included
        assert len(data["servers"]) == 1
        assert data["servers"][0]["server"] == "1.2.3.4"

    def test_empty_proxy_list(self):
        """Test SIP008 export with empty list."""
        adapter = SIP008Adapter()
        result = adapter.export([])

        data = json.loads(result)
        assert data["version"] == 1
        assert len(data["servers"]) == 0

    def test_multiple_shadowsocks(self):
        """Test SIP008 export with multiple SS proxies."""
        adapter = SIP008Adapter()
        proxies = [
            Proxy(
                config=f"ss://test{i}",
                protocol="shadowsocks",
                address=f"1.2.3.{i}",
                port=443 + i,
                details={"method": "aes-256-gcm", "password": f"pass{i}"},
                remarks=f"SS{i}",
            )
            for i in range(5)
        ]
        result = adapter.export(proxies)

        data = json.loads(result)
        assert len(data["servers"]) == 5


class TestShadowrocketAdapter:
    """Comprehensive tests for ShadowrocketAdapter."""

    def test_shadowsocks_reconstruction(self):
        """Test Shadowsocks URI reconstruction."""
        adapter = ShadowrocketAdapter()
        # Don't provide config with "://" to trigger reconstruction
        proxy = Proxy(
            config="raw_config_data",
            protocol="ss",
            address="1.2.3.4",
            port=443,
            details={"method": "aes-256-gcm", "password": "secret"},
            remarks="SR SS",
        )
        result = adapter.export([proxy])

        assert "ss://" in result
        assert "@1.2.3.4:443" in result

    def test_trojan_reconstruction(self):
        """Test Trojan URI reconstruction."""
        adapter = ShadowrocketAdapter()
        # Don't provide config with "://" to trigger reconstruction
        proxy = Proxy(
            config="raw_config_data",
            protocol="trojan",
            address="trojan.com",
            port=443,
            uuid="password123",
            remarks="SR Trojan",
        )
        result = adapter.export([proxy])

        assert "trojan://password123@trojan.com:443" in result

    def test_vmess_reconstruction(self):
        """Test VMess URI reconstruction."""
        adapter = ShadowrocketAdapter()
        proxy = Proxy(
            config="vmess://test",
            protocol="vmess",
            address="example.com",
            port=443,
            uuid="test-uuid",
            details={"aid": 0, "scy": "auto", "net": "tcp", "type": "none"},
            remarks="SR VMess",
        )
        result = adapter.export([proxy])

        assert "vmess://" in result

    def test_malformed_original_vmess_is_preserved_with_safe_name(self):
        """Malformed original VMess payloads should not abort export."""
        adapter = ShadowrocketAdapter()
        proxy = Proxy(
            config="vmess://not-json#unsafe name",
            protocol="vmess",
            address="example.com",
            port=443,
            uuid="test-uuid",
            remarks="Safe Name",
        )

        result = adapter.export([proxy])

        assert result == "vmess://not-json#Safe%20Name"

    def test_use_original_config_if_available(self):
        """Test that original config is used if it contains ://."""
        adapter = ShadowrocketAdapter()
        original_uri = "ss://YWVzLTI1Ni1nY206c2VjcmV0@1.2.3.4:443#Original"
        proxy = Proxy(
            config=original_uri,
            protocol="ss",
            address="1.2.3.4",
            port=443,
            details={"method": "aes-256-gcm", "password": "secret"},
        )
        result = adapter.export([proxy])

        # Should use original config
        assert original_uri in result

    def test_empty_export(self):
        """Test export with no proxies."""
        adapter = ShadowrocketAdapter()
        result = adapter.export([])

        assert result == ""

    def test_unsupported_protocol_skipped(self):
        """Test that unsupported protocols are skipped."""
        adapter = ShadowrocketAdapter()
        proxy = Proxy(
            config="unknown",
            protocol="unknown",
            address="test.com",
            port=443,  # No ://
        )
        result = adapter.export([proxy])

        # Should return empty since it can't reconstruct
        assert result == ""

    def test_vmess_with_tls_details(self):
        """Test VMess reconstruction with TLS details."""
        adapter = ShadowrocketAdapter()
        proxy = Proxy(
            config="vmess://test",
            protocol="vmess",
            address="example.com",
            port=443,
            uuid="test-uuid",
            details={
                "tls": "tls",
                "sni": "example.com",
                "alpn": "h2,http/1.1",
                "net": "ws",
                "path": "/path",
            },
        )
        result = adapter.export([proxy])

        # Should contain vmess://
        assert "vmess://" in result


class TestGetAdapter:
    """Tests for get_adapter function."""

    def test_get_surge_adapter(self):
        """Test getting Surge adapter."""
        adapter = get_adapter("surge")
        assert isinstance(adapter, SurgeAdapter)

    def test_get_surge_adapter_case_insensitive(self):
        """Test case insensitivity."""
        adapter = get_adapter("SURGE")
        assert isinstance(adapter, SurgeAdapter)

    def test_get_loon_adapter(self):
        """Test getting Loon adapter."""
        adapter = get_adapter("loon")
        assert isinstance(adapter, LoonAdapter)

    def test_get_quantumultx_adapter_qx(self):
        """Test getting QuantumultX adapter with 'qx'."""
        adapter = get_adapter("qx")
        assert isinstance(adapter, QuantumultXAdapter)

    def test_get_quantumultx_adapter_full_name(self):
        """Test getting QuantumultX adapter with full name."""
        adapter = get_adapter("quantumultx")
        assert isinstance(adapter, QuantumultXAdapter)

    def test_get_sip008_adapter(self):
        """Test getting SIP008 adapter."""
        adapter = get_adapter("sip008")
        assert isinstance(adapter, SIP008Adapter)

    def test_get_shadowrocket_adapter(self):
        """Test getting Shadowrocket adapter."""
        adapter = get_adapter("shadowrocket")
        assert isinstance(adapter, ShadowrocketAdapter)

    def test_get_unknown_adapter_raises_error(self):
        """Test that unknown adapter raises ValueError."""
        with pytest.raises(ValueError, match="Unknown format"):
            get_adapter("unknown_format")

    def test_get_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            get_adapter("")


class TestEdgeCases:
    """Test edge cases across all adapters."""

    def test_all_adapters_handle_empty_list(self):
        """Test that all adapters handle empty proxy list."""
        adapters = [
            SurgeAdapter(),
            LoonAdapter(),
            QuantumultXAdapter(),
            SIP008Adapter(),
            ShadowrocketAdapter(),
        ]

        for adapter in adapters:
            result = adapter.export([])
            # Should not crash
            assert isinstance(result, str)

    def test_all_adapters_handle_none_washed_outbounds(self):
        """Test that adapters handle None washed_outbounds."""
        proxy = Proxy(
            config="ss://test",
            protocol="ss",
            address="1.2.3.4",
            port=443,
            details={"method": "aes-256-gcm", "password": "pass"},
        )

        adapters = [
            SurgeAdapter(),
            LoonAdapter(),
            QuantumultXAdapter(),
            SIP008Adapter(),
            ShadowrocketAdapter(),
        ]

        for adapter in adapters:
            result = adapter.export([proxy], None)
            assert isinstance(result, str)

    def test_proxy_without_remarks(self):
        """Test proxies without remarks."""
        proxy = Proxy(
            config="ss://test",
            protocol="ss",
            address="1.2.3.4",
            port=443,
            details={"method": "aes-256-gcm", "password": "pass"},
        )

        adapter = SurgeAdapter()
        result = adapter.export([proxy])

        # Should use protocol_address as fallback
        assert "ss_1.2.3.4" in result
