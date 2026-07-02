# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprehensive tests for VLESS parser."""

import pytest
from configstream.parsers.vless import parse_vless


class TestVLESSBasic:
    """Basic VLESS parsing tests."""

    def test_vless_basic(self):
        """Standard VLESS URL with TLS."""
        proxy = parse_vless("vless://uuid@example.com:443?security=tls&type=tcp#MyServer")
        assert proxy is not None
        assert proxy.protocol == "vless"
        assert proxy.address == "example.com"
        assert proxy.port == 443
        assert proxy.uuid == "uuid"

    def test_vless_no_port_defaults_443(self):
        """VLESS without port defaults to 443."""
        proxy = parse_vless("vless://uuid@example.com")
        assert proxy is not None
        assert proxy.port == 443

    def test_vless_with_ws(self):
        """VLESS with WebSocket transport."""
        proxy = parse_vless("vless://uuid@example.com:443?type=ws&path=/ws&host=example.com&security=tls#WS")
        assert proxy is not None
        assert proxy.details.get("type") == "ws"
        assert proxy.details.get("path") == "/ws"
        assert proxy.details.get("host") == "example.com"

    def test_vless_with_grpc(self):
        """VLESS with gRPC transport."""
        proxy = parse_vless("vless://uuid@example.com:443?type=grpc&serviceName=mygrpc&security=tls#gRPC")
        assert proxy is not None
        assert proxy.details.get("type") == "grpc"
        assert proxy.details.get("serviceName") == "mygrpc"

    def test_vless_reality(self):
        """VLESS with Reality."""
        proxy = parse_vless("vless://uuid@example.com:443?security=reality&pbk=publickey&sid=1234&fp=chrome&type=tcp#Reality")
        assert proxy is not None
        assert proxy.details.get("security") == "reality"
        assert proxy.details.get("pbk") == "publickey"
        assert proxy.details.get("sid") == "1234"
        assert proxy.details.get("fp") == "chrome"

    def test_vless_xtls_direct_rejected(self):
        """XTLS-rprx-direct flow should be rejected."""
        assert parse_vless("vless://uuid@example.com:443?flow=xtls-rprx-direct") is None


class TestVLESSNoScheme:
    """VLESS without proper scheme."""

    def test_no_vless_scheme(self):
        """Config without vless:// prefix should return None."""
        assert parse_vless("http://example.com") is None
        assert parse_vless("vmess://example") is None
        assert parse_vless("") is None


class TestVLESSIPv6:
    """VLESS with IPv6 addresses."""

    def test_vless_ipv6(self):
        """VLESS with IPv6 address in brackets."""
        proxy = parse_vless("vless://uuid@[2001:db8::1]:443")
        assert proxy is not None
        assert proxy.address == "2001:db8::1"
        assert proxy.port == 443

    def test_vless_ipv6_no_port(self):
        """VLESS with IPv6 and no port."""
        proxy = parse_vless("vless://uuid@[::1]")
        assert proxy is not None
        assert proxy.address == "::1"
        assert proxy.port == 443

    def test_vless_ipv6_malformed_brackets(self):
        """VLESS with malformed IPv6 brackets should return None."""
        assert parse_vless("vless://uuid@[2001:db8::1:443") is None


class TestVLESSNameAndRemarks:
    """VLESS name/remark handling."""

    def test_vless_with_remark(self):
        """VLESS with fragment remark."""
        proxy = parse_vless("vless://uuid@host:443?security=tls#My%20Server")
        assert proxy is not None
        assert proxy.remarks == "My Server"

    def test_vless_no_remark(self):
        """VLESS without remark should have empty remarks."""
        proxy = parse_vless("vless://uuid@host:443")
        assert proxy is not None
        assert proxy.remarks == ""
