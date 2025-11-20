import pytest
from configstream.models import Proxy
from configstream.adapters import to_clash_proxy, to_singbox_outbound


@pytest.fixture
def vmess_ws_proxy():
    """A sample VMess proxy with WebSocket transport."""
    return Proxy(
        config="vmess://...",
        protocol="vmess",
        address="test.com",
        port=443,
        uuid="a-b-c-d",
        remarks="Test-VMess",
        details={
            "net": "ws",
            "security": "tls",
            "host": "test.com",
            "aid": "0",
            "scy": "auto",
            "sni": "test.com",
            "path": "/ws-path",
        },
    )


@pytest.fixture
def vless_reality_proxy():
    """A sample VLESS proxy with Reality security."""
    return Proxy(
        config="vless://...",
        protocol="vless",
        address="1.2.3.4",
        port=443,
        uuid="e-f-g-h",
        remarks="Test-VLESS-Reality",
        details={
            "security": "reality",
            "pbk": "pub-key",
            "sid": "short-id",
            "fp": "chrome",
            "flow": "xtls-rprx-vision",
            "sni": "cdn.com",
        },
    )


# --- Clash Adapter Tests ---


def test_clash_adapter_vmess(vmess_ws_proxy):
    clash_config = to_clash_proxy(vmess_ws_proxy)

    assert clash_config is not None
    assert clash_config["type"] == "vmess"
    assert clash_config["name"] == "Test-VMess"
    assert clash_config["server"] == "test.com"
    assert clash_config["port"] == 443
    assert clash_config["uuid"] == "a-b-c-d"
    assert clash_config["network"] == "ws"
    assert clash_config["tls"] is True
    assert clash_config["servername"] == "test.com"
    assert clash_config["ws-opts"]["path"] == "/ws-path"
    assert clash_config["ws-opts"]["headers"]["Host"] == "test.com"


def test_clash_adapter_vless_reality(vless_reality_proxy):
    clash_config = to_clash_proxy(vless_reality_proxy)

    assert clash_config is not None
    assert clash_config["type"] == "vless"
    assert clash_config["flow"] == "xtls-rprx-vision"
    assert clash_config["client-fingerprint"] == "chrome"
    assert clash_config["reality-opts"]["public-key"] == "pub-key"
    assert clash_config["reality-opts"]["short-id"] == "short-id"


# --- Sing-box Adapter Tests ---


def test_singbox_adapter_vmess(vmess_ws_proxy):
    singbox_config = to_singbox_outbound(vmess_ws_proxy)

    assert singbox_config is not None
    assert singbox_config["type"] == "vmess"
    assert singbox_config["tag"] == "Test-VMess"
    assert singbox_config["server"] == "test.com"
    assert singbox_config["server_port"] == 443
    assert singbox_config["uuid"] == "a-b-c-d"
    assert singbox_config["tls"]["enabled"] is True
    assert singbox_config["tls"]["server_name"] == "test.com"
    assert singbox_config["transport"]["type"] == "ws"
    assert singbox_config["transport"]["path"] == "/ws-path"
    assert singbox_config["transport"]["headers"]["Host"] == "test.com"


def test_singbox_adapter_vless_reality(vless_reality_proxy):
    singbox_config = to_singbox_outbound(vless_reality_proxy)

    assert singbox_config is not None
    assert singbox_config["type"] == "vless"
    assert singbox_config["flow"] == "xtls-rprx-vision"
    assert singbox_config["tls"]["reality"]["enabled"] is True
    assert singbox_config["tls"]["reality"]["public_key"] == "pub-key"
    assert singbox_config["tls"]["reality"]["short_id"] == "short-id"
    assert singbox_config["tls"]["utls"]["fingerprint"] == "chrome"
