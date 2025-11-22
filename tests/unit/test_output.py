import pytest
from configstream.output import (
    generate_base64_subscription,
    generate_clash_config,
    generate_singbox_config,
    serialize_proxy,
)
from configstream.models import Proxy


@pytest.fixture
def sample_proxies():
    return [
        Proxy(
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            uuid="a1b2c3d4",
            config="vmess://test",
            details={"tls": True, "net": "ws"},
            country_code="US",
            remarks="Test Proxy",
        ),
        Proxy(
            protocol="shadowsocks",
            address="8.8.8.8",
            port=8388,
            config="ss://test",
            details={"method": "aes-256-gcm", "password": "pass"},
            country_code="DE",
            remarks="SS Proxy",
        ),
    ]


def test_generate_base64(sample_proxies):
    output = generate_base64_subscription(sample_proxies)
    assert isinstance(output, str)
    assert len(output) > 0


def test_generate_clash(sample_proxies):
    # Ensure is_working is True for proxies to be included
    for p in sample_proxies:
        p.is_working = True
    output = generate_clash_config(sample_proxies)
    assert "proxies:" in output
    assert "name: Test Proxy" in output or "name: US 01 | VMESS" in output


def test_generate_singbox(sample_proxies):
    output = generate_singbox_config(sample_proxies)
    assert '"type": "vmess"' in output
    assert '"type": "shadowsocks"' in output


def test_serialize_proxy(sample_proxies):
    data = serialize_proxy(sample_proxies[0])
    assert data["protocol"] == "vmess"
    assert data["address"] == "1.1.1.1"
    assert data["country"] == "US"
