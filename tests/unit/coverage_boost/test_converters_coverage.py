# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import re
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
            "sni": "example.com",
            "tls": "tls",
        },
    )


def test_to_singbox_outbound_wireguard():
    proxy = Proxy(
        config="wireguard://test",
        protocol="wireguard",
        address="1.1.1.1",
        port=51820,
        details={
            "private_key": "privkey",
            "peer_public_key": "pubkey",
            "address": "10.0.0.2/32",
            "mtu": "1280",
            "reserved": "1,2,3",
        },
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["type"] == "wireguard"
    # Improved regex for IP validation (private CIDR range)
    # Matches: 172.(16-31).x.x/32
    # The actual code generates a unique IP in the 172.16.0.0/12 block.
    # We use regex to be robust against minor changes in hashing.
    assert re.match(r"^172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}/32$", out["local_address"])
    assert out["private_key"] == "privkey"
    assert out["peer_public_key"] == "pubkey"
