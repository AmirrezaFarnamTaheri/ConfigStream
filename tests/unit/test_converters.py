# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from configstream.models import Proxy
from configstream.converters import to_clash_proxy, to_singbox_outbound


@pytest.fixture
def sample_proxy():
    return Proxy(
        config="vmess://...",
        protocol="vmess",
        address="1.1.1.1",
        port=443,
        uuid="uuid-1",
        latency=50.0,
        is_working=True,
        country_code="US",
        details={"aid": 0, "net": "ws", "tls": "tls", "path": "/ws"},
    )


def test_to_clash_proxy_vmess(sample_proxy):
    clash = to_clash_proxy(sample_proxy)
    assert clash["type"] == "vmess"
    assert clash["server"] == "1.1.1.1"
    assert clash["network"] == "ws"
    assert clash["tls"] is True


def test_to_singbox_outbound_vmess(sample_proxy):
    sing = to_singbox_outbound(sample_proxy)
    assert sing["type"] == "vmess"
    assert sing["server"] == "1.1.1.1"
    assert sing["transport"]["type"] == "ws"
    assert sing["tls"]["enabled"] is True


def test_safe_int_conversion():
    from configstream.converters import safe_int_conversion

    assert safe_int_conversion("123") == 123
    assert safe_int_conversion(b"123") == 123
    assert safe_int_conversion(None) == 0
    assert safe_int_conversion("abc") == 0


def test_to_clash_proxy_ws_grpc():
    """Clash converter: WS and gRPC transport options."""
    p_ws = Proxy(
        config="vless://...",
        protocol="vless",
        address="1.2.3.4",
        port=443,
        uuid="uuid",
        is_working=True,
        details={"network": "ws", "path": "/ws", "host": "host.com", "security": "tls"},
    )
    clash = to_clash_proxy(p_ws)
    assert clash["network"] == "ws"
    assert clash["ws-opts"]["path"] == "/ws"
    assert clash["ws-opts"]["headers"]["Host"] == "host.com"
    assert clash["tls"] is True

    p_grpc = Proxy(
        config="vmess://...",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        uuid="uuid",
        is_working=True,
        details={"network": "grpc", "serviceName": "grpc-service", "security": "tls"},
    )
    clash = to_clash_proxy(p_grpc)
    assert clash["network"] == "grpc"
    assert clash["grpc-opts"]["grpc-service-name"] == "grpc-service"
    assert clash["tls"] is True


def test_to_singbox_outbound_ws_reality():
    """Sing-box converter: WS transport and Reality TLS."""
    p = Proxy(
        config="vless://...",
        protocol="vless",
        address="1.2.3.4",
        port=443,
        uuid="uuid",
        details={
            "net": "ws",
            "path": "/ws",
            "host": "host.com",
            "security": "reality",
            "pbk": "pbk",
            "sid": "sid",
            "fp": "chrome",
        },
    )
    sb = to_singbox_outbound(p)
    assert sb["transport"]["type"] == "ws"
    assert sb["transport"]["path"] == "/ws"
    assert sb["transport"]["headers"]["Host"] == "host.com"
    assert sb["tls"]["enabled"] is True
    assert sb["tls"]["utls"]["fingerprint"] == "chrome"
    assert sb["tls"]["reality"]["public_key"] == "pbk"
