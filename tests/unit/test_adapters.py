import pytest
from configstream.adapters import (
    get_adapter,
    SurgeAdapter,
    LoonAdapter,
    QuantumultXAdapter,
    SIP008Adapter,
)
from configstream.models import Proxy


@pytest.fixture
def sample_proxies():
    return [
        Proxy(
            config="ss://method:pass@1.1.1.1:8080#Example",
            protocol="shadowsocks",
            address="1.1.1.1",
            port=8080,
            remarks="Example",
            details={"method": "aes-256-gcm", "password": "pass"},
        ),
        Proxy(
            config="vmess://...",
            protocol="vmess",
            address="2.2.2.2",
            port=443,
            uuid="uuid-1234",
            remarks="VMess Node",
            details={"method": "auto"},
        ),
    ]


def test_get_adapter():
    assert isinstance(get_adapter("surge"), SurgeAdapter)
    assert isinstance(get_adapter("loon"), LoonAdapter)
    assert isinstance(get_adapter("qx"), QuantumultXAdapter)
    assert isinstance(get_adapter("sip008"), SIP008Adapter)
    with pytest.raises(ValueError):
        get_adapter("invalid")


def test_surge_export(sample_proxies):
    adapter = SurgeAdapter()
    output = adapter.export(sample_proxies)
    assert "# Surge Policy Export" in output
    assert (
        "Example = ss, 1.1.1.1, 8080, encrypt-method=aes-256-gcm, password=pass"
        in output
    )
    assert "VMess Node = vmess, 2.2.2.2, 443, username=uuid-1234" in output


def test_loon_export(sample_proxies):
    adapter = LoonAdapter()
    output = adapter.export(sample_proxies)
    assert "# Loon Proxy Export" in output
    assert 'Example = shadowsocks, 1.1.1.1, 8080, aes-256-gcm, "pass"' in output


def test_qx_export(sample_proxies):
    adapter = QuantumultXAdapter()
    output = adapter.export(sample_proxies)
    assert (
        "shadowsocks=Example: 1.1.1.1, 8080, method=aes-256-gcm, password=pass"
        in output
    )


def test_sip008_export(sample_proxies):
    adapter = SIP008Adapter()
    output = adapter.export(sample_proxies)
    import json

    data = json.loads(output)
    assert data["version"] == 1
    assert (
        len(data["servers"]) == 1
    )  # Only SS is supported in this basic SIP008 adapter logic
    assert data["servers"][0]["server"] == "1.1.1.1"
