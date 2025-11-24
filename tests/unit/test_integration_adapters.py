import pytest
from configstream.adapters import get_adapter
from configstream.models import Proxy


@pytest.fixture
def sample_proxies():
    return [
        Proxy(
            config="vmess://uuid@1.1.1.1:443",
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            uuid="uuid",
            remarks="Test Node",
        )
    ]


@pytest.fixture
def washed_outbounds():
    return [
        {
            "type": "vmess",
            "tag": "RELAY-CHAIN-123",
            "server": "1.1.1.1",
            "server_port": 443,
            "uuid": "uuid",
        },
        {
            "type": "wireguard",
            "tag": "🛡️ Secure-US-1",
            "server": "162.159.192.1",
            "server_port": 2408,
            "private_key": "priv",
            "peer_public_key": "pub",
            "detour": "RELAY-CHAIN-123",
        },
    ]


def test_surge_adapter_export(sample_proxies, washed_outbounds):
    adapter = get_adapter("surge")
    output = adapter.export(sample_proxies, washed_outbounds)

    assert "Test Node = vmess" in output
    assert "🛡️ Secure-US-1 = wireguard" in output
    assert "underlying-proxy=RELAY-CHAIN-123" in output
    assert "RELAY-CHAIN-123 = vmess" in output


def test_loon_adapter_export(sample_proxies, washed_outbounds):
    adapter = get_adapter("loon")
    output = adapter.export(sample_proxies, washed_outbounds)

    assert "Test Node = vmess" in output
    assert "🛡️ Secure-US-1 = wireguard" in output
    assert "proxy=RELAY-CHAIN-123" in output  # Loon syntax
    assert "RELAY-CHAIN-123 = vmess" in output
