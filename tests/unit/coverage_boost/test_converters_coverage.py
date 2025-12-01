import pytest
from configstream.converters import to_singbox_outbound
from configstream.models import Proxy


@pytest.fixture
def base_proxy():
    return Proxy(
        config="vmess://test",
        protocol="vmess",
        uuid="uuid",
        address="1.1.1.1",
        port=443,
        details={
            "alterId": 0,
            "security": "auto",
            "net": "ws",
            "ws-path": "/path",
            "host": "example.com",
            "sni": "example.com",  # Added sni
            "tls": "tls",
        },
    )


def test_to_singbox_outbound_vmess(base_proxy):
    out = to_singbox_outbound(base_proxy)
    assert out is not None
    assert out["type"] == "vmess"
    assert out["server"] == "1.1.1.1"
    assert out["server_port"] == 443
    assert out["uuid"] == "uuid"
    assert out["transport"]["type"] == "ws"
    assert out["tls"]["enabled"] is True
    assert out["tls"]["server_name"] == "example.com"


def test_to_singbox_outbound_vless():
    proxy = Proxy(
        config="vless://test",
        protocol="vless",
        uuid="uuid",
        address="1.1.1.1",
        port=443,
        details={
            "net": "grpc",
            "serviceName": "grpc-service",
            "security": "reality",
            "pbk": "public-key",
            "fp": "chrome",
            "sni": "example.com",
            "sid": "short-id",
        },
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["type"] == "vless"
    assert out["transport"]["type"] == "grpc"
    assert out["tls"]["enabled"] is True
    assert out["tls"]["reality"]["enabled"] is True
    assert out["tls"]["reality"]["public_key"] == "public-key"
    assert out["tls"]["reality"]["short_id"] == "short-id"


def test_to_singbox_outbound_trojan():
    proxy = Proxy(
        config="trojan://test",
        protocol="trojan",
        uuid="password",
        address="1.1.1.1",
        port=443,
        details={"net": "tcp", "sni": "example.com"},
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["type"] == "trojan"
    assert out["password"] == "password"
    assert out["tls"]["enabled"] is True
    assert out["tls"]["server_name"] == "example.com"


def test_to_singbox_outbound_shadowsocks():
    proxy = Proxy(
        config="ss://test",
        protocol="shadowsocks",
        uuid="password",
        address="1.1.1.1",
        port=8388,
        details={
            "password": "password",
            "method": "aes-256-gcm",
            "plugin": "v2ray-plugin",
            "plugin_opts": "server;host=example.com",
        },
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["type"] == "shadowsocks"
    assert out["method"] == "aes-256-gcm"
    assert out["plugin"] == "v2ray-plugin"
    assert "plugin_opts" in out


def test_to_singbox_outbound_hysteria2():
    proxy = Proxy(
        config="hysteria2://test",
        protocol="hysteria2",
        uuid="auth",
        address="1.1.1.1",
        port=443,
        details={
            "sni": "example.com",
            "allowInsecure": "1",
            "obfs": "salam",
            "obfs-password": "password",
        },
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["type"] == "hysteria2"
    assert out["password"] == "auth"
    assert out["tls"]["enabled"] is True
    assert out["tls"]["insecure"] is True


def test_to_singbox_outbound_tuic():
    proxy = Proxy(
        config="tuic://test",
        protocol="tuic",
        uuid="uuid",
        address="1.1.1.1",
        port=443,
        details={
            "password": "password",
            "sni": "example.com",
            "congestion_controller": "bbr",
        },
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["type"] == "tuic"
    assert out["uuid"] == "uuid"
    assert out["password"] == "password"
    assert out["congestion_control"] == "bbr"


def test_to_singbox_outbound_unknown_protocol():
    proxy = Proxy(
        config="unknown://test",
        protocol="unknown",
        address="1.1.1.1",
        port=80,
        details={},
    )
    out = to_singbox_outbound(proxy)
    assert out is None


def test_to_singbox_outbound_wireguard():
    proxy = Proxy(
        config="wireguard://test",
        protocol="wireguard",
        address="1.1.1.1",
        port=51820,
        details={
            "private_key": "privkey",  # Changed from private-key
            "peer_public_key": "pubkey",  # Changed from public-key
            "address": "10.0.0.2/32",
            "mtu": "1280",
            "reserved": "1,2,3",
        },
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["type"] == "wireguard"
    assert out["local_address"] == ["172.16.196.2/32"]
    assert out["private_key"] == "privkey"
    assert out["peer_public_key"] == "pubkey"


def test_add_transport_sb_coverage():
    # Test indirect coverage via proxy conversion
    proxy = Proxy(
        config="vmess://test",
        protocol="vmess",
        uuid="uuid",
        address="1.1.1.1",
        port=443,
        details={"net": "http", "path": "/p", "host": "h"},  # Changed http-path->path
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["transport"]["type"] == "http"
    assert out["transport"]["path"] == "/p"
    assert out["transport"]["host"] == ["h"]


def test_add_tls_sb_coverage():
    # Test indirect coverage via proxy conversion
    proxy = Proxy(
        config="trojan://test",
        protocol="trojan",
        uuid="password",
        address="1.1.1.1",
        port=443,
        details={"allowInsecure": "1", "sni": "example.com"},
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["tls"]["insecure"] is True
