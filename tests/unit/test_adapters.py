from configstream.adapters import LoonAdapter, QuantumultXAdapter, SurgeAdapter, SIP008Adapter, get_adapter
from configstream.models import Proxy
import pytest

def test_loon_adapter():
    adapter = LoonAdapter()
    proxy = Proxy(
        config="dummy",
        protocol="shadowsocks",
        address="1.2.3.4",
        port=443,
        details={"method": "aes-256-gcm", "password": "pass"},
        remarks="Test Proxy"
    )
    output = adapter.export([proxy])
    assert "Test Proxy = shadowsocks, 1.2.3.4, 443, aes-256-gcm, \"pass\"" in output

def test_quantumultx_adapter():
    adapter = QuantumultXAdapter()
    proxy = Proxy(
        config="dummy",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        uuid="uuid-1234",
        details={"method": "chacha20-poly1305"},
        remarks="Test VMess"
    )
    output = adapter.export([proxy])
    assert "vmess=Test VMess: 1.2.3.4, 443, method=chacha20-poly1305, password=uuid-1234" in output

def test_surge_adapter():
    adapter = SurgeAdapter()
    proxy = Proxy(
        config="dummy",
        protocol="http",
        address="1.2.3.4",
        port=80,
        uuid="user",
        details={"password": "pass"},
        remarks="Test HTTP"
    )
    output = adapter.export([proxy])
    assert "Test HTTP = http, 1.2.3.4, 80, username=user, password=pass" in output

def test_get_adapter():
    assert isinstance(get_adapter("surge"), SurgeAdapter)
    assert isinstance(get_adapter("loon"), LoonAdapter)
    assert isinstance(get_adapter("qx"), QuantumultXAdapter)
    assert isinstance(get_adapter("quantumultx"), QuantumultXAdapter)
    assert isinstance(get_adapter("sip008"), SIP008Adapter)

    with pytest.raises(ValueError):
        get_adapter("invalid")
