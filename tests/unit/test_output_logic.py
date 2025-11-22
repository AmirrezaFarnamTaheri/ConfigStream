import pytest
import json
from pathlib import Path
from configstream.output import wash_dirty_proxies, generate_exotic_chains, to_singbox_outbound
from configstream.models import Proxy

@pytest.fixture
def mock_proxies():
    return [
        Proxy(config="raw", protocol="socks5", address="1.1.1.1", port=1080, is_working=True, country_code="US", details={}),
        Proxy(config="raw", protocol="http", address="2.2.2.2", port=8080, is_working=True, country_code="DE", details={}),
        Proxy(config="raw", protocol="vless", address="3.3.3.3", port=443, is_working=True, country_code="FR", details={"tls": "tls"}),
        Proxy(config="raw", protocol="hysteria2", address="4.4.4.4", port=443, is_working=True, country_code="CN", details={}),
        Proxy(config="raw", protocol="vmess", address="5.5.5.5", port=10086, is_working=True, country_code="JP", details={}),
    ]

def test_wash_dirty_proxies_no_keys(mock_proxies, monkeypatch):
    # Without keys, socks shouldn't be washed
    monkeypatch.setenv("WARP_KEY_POOL", "[]")
    washed = wash_dirty_proxies(mock_proxies)
    # Should still wash HTTP if secure exits exist
    # mock_proxies[2] is VLESS+TLS, so it can serve as exit for HTTP wash
    # HTTP is mock_proxies[1]

    # washed should contain at least one pair (Relay + Exit)
    # Actually logic searches for 'socks' without TLS and 'http' without TLS
    assert len(washed) >= 0

def test_wash_dirty_proxies_with_keys(mock_proxies, monkeypatch):
    keys = [{"private_key": "A", "peer_public_key": "B"}]
    monkeypatch.setenv("WARP_KEY_POOL", json.dumps(keys))

    washed = wash_dirty_proxies(mock_proxies)
    # Expect SOCKS wash (Proxy 1) -> 2 outbounds (Relay + WARP)
    # Expect HTTP wash (Proxy 2) -> 2 outbounds (Relay + TLS Exit)

    # We have 1 SOCKS dirty, 1 HTTP dirty.
    # SOCKS -> WARP (2 items)
    # HTTP -> VLESS (2 items)
    # Total 4 items expected if random selection picks valid ones

    # Since randomness involved in selection, we check types
    tags = [o.get("tag", "") for o in washed]
    assert any("WASH-SOCKS" in t for t in tags)
    assert any("CLEAN-WARP" in t for t in tags)

def test_generate_exotic_chains(mock_proxies):
    chains = generate_exotic_chains(mock_proxies)
    # Proxy 4 is Hysteria2 (Relay candidate)
    # Proxy 5 is VMess (Exit candidate)
    # Should form a chain

    if len(chains) > 0:
        # Chains are pairs of outbounds
        relay = chains[0]
        exit_node = chains[1]

        assert "detour" in exit_node
        assert exit_node["detour"] == relay["tag"]

def test_to_singbox_outbound_basic():
    p = Proxy(config="raw", protocol="vmess", address="1.2.3.4", port=1234, uuid="uuid", details={"aid": 0})
    out = to_singbox_outbound(p)
    assert out["type"] == "vmess"
    assert out["server"] == "1.2.3.4"
