import pytest
from configstream.output import to_clash_proxy, to_singbox_outbound
from configstream.models import Proxy

def test_output_transport_clash():
    # WS
    p_ws = Proxy(
        config="vless://...",
        protocol="vless",
        address="1.2.3.4",
        port=443,
        uuid="uuid",
        details={"net": "ws", "path": "/ws", "host": "host.com", "tls": "tls"}
    )
    clash = to_clash_proxy(p_ws)
    assert clash["network"] == "ws"
    assert clash["ws-opts"]["path"] == "/ws"
    assert clash["ws-opts"]["headers"]["Host"] == "host.com"
    assert clash["tls"] is True

    # GRPC
    p_grpc = Proxy(
        config="vmess://...",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        uuid="uuid",
        details={"net": "grpc", "serviceName": "grpc-service", "security": "tls"}
    )
    clash = to_clash_proxy(p_grpc)
    assert clash["network"] == "grpc"
    assert clash["grpc-opts"]["grpc-service-name"] == "grpc-service"
    assert clash["tls"] is True

def test_output_transport_singbox():
    # WS
    p_ws = Proxy(
        config="vless://...",
        protocol="vless",
        address="1.2.3.4",
        port=443,
        uuid="uuid",
        details={"net": "ws", "path": "/ws", "host": "host.com", "security": "reality", "pbk": "pbk", "sid": "sid", "fp": "chrome"}
    )
    sb = to_singbox_outbound(p_ws)
    assert sb["transport"]["type"] == "ws"
    assert sb["transport"]["path"] == "/ws"
    assert sb["transport"]["headers"]["Host"] == "host.com"
    assert sb["tls"]["enabled"] is True
    assert sb["tls"]["utls"]["fingerprint"] == "chrome"
    assert sb["tls"]["reality"]["public_key"] == "pbk"
