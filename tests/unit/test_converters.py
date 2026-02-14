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
