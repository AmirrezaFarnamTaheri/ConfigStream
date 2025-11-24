import pytest
from configstream.adapters import (
    get_adapter,
    SurgeAdapter,
    QuantumultXAdapter,
    LoonAdapter,
    ShadowrocketAdapter,
    SIP008Adapter,
)
from configstream.models import Proxy


@pytest.fixture
def proxies():
    p = Proxy(
        config="vless://1",
        protocol="vless",
        address="1.1.1.1",
        port=443,
        uuid="u1",
        is_working=True,
        latency=100,
        country_code="US",
        details={"security": "tls", "sni": "example.com"},
        id="p1",
        remarks="Test Node",
    )
    p_ss = Proxy(
        config="ss://...",
        protocol="shadowsocks",
        address="2.2.2.2",
        port=1080,
        uuid="",
        is_working=True,
        latency=50,
        country_code="JP",
        details={"method": "chacha20-ietf-poly1305", "password": "pass"},
        remarks="SS Node",
    )
    p_vmess = Proxy(
        config="vmess://...",
        protocol="vmess",
        address="3.3.3.3",
        port=80,
        uuid="u3",
        is_working=True,
        latency=100,
        country_code="CN",
        details={"method": "chacha20-poly1305"},
        remarks="VMess Node",
    )
    return [p, p_ss, p_vmess]


def test_get_adapter():
    assert isinstance(get_adapter("surge"), SurgeAdapter)
    assert isinstance(get_adapter("qx"), QuantumultXAdapter)
    assert isinstance(get_adapter("loon"), LoonAdapter)
    assert isinstance(get_adapter("shadowrocket"), ShadowrocketAdapter)
    assert isinstance(get_adapter("sip008"), SIP008Adapter)

    with pytest.raises(ValueError):
        get_adapter("invalid")


def test_surge_export(proxies):
    adapter = SurgeAdapter()
    output = adapter.export(proxies)
    assert "# Surge Policy Export" in output
    assert "SS Node = ss, 2.2.2.2, 1080" in output
    assert "VMess Node = vmess, 3.3.3.3, 80" in output


def test_qx_export(proxies):
    adapter = QuantumultXAdapter()
    output = adapter.export(proxies)
    assert "shadowsocks=SS Node: 2.2.2.2, 1080" in output
    assert "vmess=VMess Node: 3.3.3.3, 80" in output


def test_loon_export(proxies):
    adapter = LoonAdapter()
    output = adapter.export(proxies)
    assert "# Loon Proxy Export" in output
    assert (
        'SS Node = shadowsocks, 2.2.2.2, 1080, chacha20-ietf-poly1305, "pass"' in output
    )
    # Fix expectation: Loon adapter uses the method from details if present
    assert 'VMess Node = vmess, 3.3.3.3, 80, chacha20-poly1305, "u3"' in output


def test_shadowrocket_export(proxies):
    adapter = ShadowrocketAdapter()
    output = adapter.export(proxies)
    assert "ss://" in output
    assert "vmess://" in output


def test_sip008_export(proxies):
    adapter = SIP008Adapter()
    output = adapter.export(proxies)
    import json

    data = json.loads(output)
    assert len(data["servers"]) == 1
    assert data["servers"][0]["server"] == "2.2.2.2"


def test_adapter_with_washed(proxies):
    adapter = SurgeAdapter()
    washed = [{"tag": "🛡️ Secure", "type": "wireguard", "detour": "relay"}]
    output = adapter.export(proxies, washed)
    assert "SS Node" in output
