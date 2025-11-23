
import pytest
import json
from src.configstream.intelligence.washer import (
    ProxyWasher,
    create_chain,
    generate_smart_chains,
)
from src.configstream.models import Proxy
from unittest.mock import MagicMock, patch

@pytest.fixture
def sample_warp_keys():
    return json.dumps([
        {"private_key": "key1", "peer_public_key": "pub1", "id": "w1"},
        {"private_key": "key2", "peer_public_key": "pub2", "id": "w2"},
    ])

def test_proxy_washer_init(sample_warp_keys):
    washer = ProxyWasher(sample_warp_keys)
    assert len(washer.warp_keys) == 2

    # Invalid JSON
    washer = ProxyWasher("{invalid")
    assert washer.warp_keys == []

    # Empty
    washer = ProxyWasher("")
    assert washer.warp_keys == []

def test_get_consistent_exit(sample_warp_keys):
    washer = ProxyWasher(sample_warp_keys)
    exit1 = washer._get_consistent_exit("proxy1", washer.warp_keys)
    exit2 = washer._get_consistent_exit("proxy1", washer.warp_keys)
    assert exit1 == exit2

    exit3 = washer._get_consistent_exit("proxy2", washer.warp_keys)
    # Might differ or same depending on hash

    assert washer._get_consistent_exit("p", []) is None

@patch("src.configstream.intelligence.washer.to_singbox_outbound")
def test_wash_batch(mock_to_sb, sample_warp_keys):
    # Use side_effect to return a NEW dict each time
    mock_to_sb.side_effect = lambda p: {"tag": "original", "type": "shadowsocks"}

    washer = ProxyWasher(sample_warp_keys)
    proxies = [
        Proxy(config="s1", protocol="ss", address="1.1", port=80, is_working=True, tags=["dirty_ip"], country_code="US", uuid="u1"),
        Proxy(config="s2", protocol="ss", address="2.2", port=80, is_working=True, tags=["insecure"], country_code="DE", uuid="u2"),
        Proxy(config="s3", protocol="ss", address="3.3", port=80, is_working=True, tags=["clean"], country_code="FR", uuid="u3"), # skipped
    ]

    outbounds, washed_ids = washer.wash_batch(proxies)
    assert len(outbounds) == 4 # 2 relays + 2 warps
    assert len(washed_ids) == 2
    assert "s1" in washed_ids or "u1" in str(washed_ids) # ID uses uuid or config

    # Check structure
    # outbounds order: relay1, warp1, relay2, warp2
    relay_out1 = outbounds[0]
    warp_out1 = outbounds[1]

    assert relay_out1["tag"].startswith("RELAY-")
    assert warp_out1["type"] == "wireguard"
    assert warp_out1["detour"] == relay_out1["tag"]

@patch("src.configstream.intelligence.washer.to_singbox_outbound")
def test_wash_batch_no_warp_keys(mock_to_sb):
    washer = ProxyWasher("")
    proxies = [Proxy(config="s1", protocol="ss", address="1.1", port=80, is_working=True, tags=["dirty_ip"])]
    outbounds, _ = washer.wash_batch(proxies)
    assert len(outbounds) == 0

@patch("src.configstream.intelligence.washer.to_singbox_outbound")
def test_create_chain(mock_to_sb):
    mock_to_sb.side_effect = lambda p: {"tag": "t", "type": "ss"}
    r = Proxy(config="r", protocol="ss", address="1.1", port=80, country="US", uuid="u1")
    e = Proxy(config="e", protocol="vmess", address="2.2", port=443, country="DE", uuid="u2")

    chain = create_chain(r, e, "TEST")
    assert len(chain) == 2
    assert chain[0]["tag"].startswith("TEST-RELAY-")
    assert chain[1]["detour"] == chain[0]["tag"]

    # Test missing conversion
    mock_to_sb.side_effect = None
    mock_to_sb.return_value = None
    assert create_chain(r, e, "TEST") == []

@patch("src.configstream.intelligence.washer.create_chain")
def test_generate_smart_chains(mock_create_chain):
    # Mock create_chain to return list of 2 dicts
    mock_create_chain.return_value = [{"tag": "r"}, {"tag": "e"}]

    proxies = [
        Proxy(config="ir1", protocol="ss", address="1.1.1.1", port=80, country_code="IR", is_working=True),
        Proxy(config="us1", protocol="vmess", address="2.2.2.2", port=443, country_code="US", is_working=True),
        Proxy(config="ipv6", protocol="ss", address="[2001::1]", port=80, country_code="FR", is_working=True),
        Proxy(config="fast", protocol="hysteria2", address="3.3.3.3", port=443, country_code="DE", is_working=True),
    ]

    chains = generate_smart_chains(proxies)
    assert "intranet" in chains
    assert "ipv6" in chains
    assert "streamer" in chains
    assert "experimental" in chains

    assert mock_create_chain.called
