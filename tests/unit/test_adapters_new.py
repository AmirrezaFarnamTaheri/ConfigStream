from configstream.adapters import get_adapter, ShadowrocketAdapter
from configstream.models import Proxy


def test_shadowrocket_adapter_existence():
    adapter = get_adapter("shadowrocket")
    assert isinstance(adapter, ShadowrocketAdapter)


def test_shadowrocket_export():
    proxies = [
        Proxy(
            config="ss://test-config",
            protocol="shadowsocks",
            address="1.2.3.4",
            port=80,
            remarks="test1",
        ),
        Proxy(
            config="vmess://test-config-2",
            protocol="vmess",
            address="5.6.7.8",
            port=443,
            remarks="test2",
        ),
    ]

    adapter = get_adapter("shadowrocket")
    output = adapter.export(proxies)

    assert "ss://test-config" in output
    assert "vmess://test-config-2" in output
    assert len(output.splitlines()) == 2
