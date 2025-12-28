from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.intelligence.washer.core import ProxyWasher
from configstream.models import Proxy


@pytest.fixture
def mock_warp_keys():
    return '[{"private_key": "priv1", "peer_public_key": "pub1", "id": "key1"}, {"private_key": "priv2", "peer_public_key": "pub2", "id": "key2"}]'


@pytest.fixture
def washer(mock_warp_keys):
    return ProxyWasher(mock_warp_keys)


@pytest.mark.asyncio
async def test_washer_get_clean_endpoint(washer):
    # Test default
    washer.clean_ips = []
    ep = washer._get_clean_endpoint("test")
    if isinstance(ep, tuple):
        ep = ep[0]
    assert ep in [
        "162.159.192.1",
        "162.159.193.10",
        "162.159.195.5",
    ]

    # Test with IPs
    washer.clean_ips = ["1.1.1.1", "2.2.2.2"]
    # Deterministic check
    ep = washer._get_clean_endpoint("test")
    if isinstance(ep, tuple):
        ip = ep[0]
    else:
        ip = ep
    assert ip in washer.clean_ips


@pytest.mark.asyncio
async def test_washer_wash_batch(washer):
    proxies = [
        Proxy(
            config="vless://1",
            protocol="vless",
            address="1.1.1.1",
            port=443,
            uuid="u1",
            country="US",
            latency=100,
        ),
        Proxy(
            config="vless://2",
            protocol="vless",
            address="2.2.2.2",
            port=443,
            uuid="u2",
            country="DE",
            latency=50,
        ),
    ]
    # Mark them working
    for p in proxies:
        p.is_working = True

    with patch(
        "configstream.intelligence.washer.core.to_singbox_outbound",
        return_value={"type": "vless"},
    ):
        outbounds, ids, skips = washer.wash_batch(proxies)
        assert len(ids) == 2
        assert len(outbounds) == 4  # 2 relays + 2 wireguard exits


@pytest.mark.asyncio
async def test_washer_wash_batch_no_working(washer):
    proxies = [
        Proxy(
            config="vless://1",
            protocol="vless",
            address="1.1.1.1",
            port=443,
            uuid="u1",
            country="US",
            latency=None,
        ),
    ]
    # Default is not working
    outbounds, ids, skips = washer.wash_batch(proxies)
    assert len(ids) == 0


def test_washer_split_brain_protection(washer):
    # Verify max seen chains limit logic (indirectly)
    # LRUCache behaves like a dict but has maxsize
    washer.seen_chains.clear()

    # Fill cache up to limit (mock small limit via private usage if possible, or just check type)
    # Since we can't easily change maxsize of existing LRUCache, we just verify it behaves like dict
    washer.seen_chains["chain1"] = True
    assert "chain1" in washer.seen_chains

    # Verify logic in wash_batch respects it
    # We can mock seen_chains
    washer.seen_chains = MagicMock()
    washer.seen_chains.__contains__.return_value = True  # Simulate duplicate

    proxies = [
        Proxy(
            config="vless://1",
            protocol="vless",
            address="1.1.1.1",
            port=443,
            uuid="u1",
            country="US",
            latency=100,
        )
    ]
    proxies[0].is_working = True

    with patch(
        "configstream.intelligence.washer.core.to_singbox_outbound",
        return_value={"type": "vless"},
    ):
        outbounds, ids, skips = washer.wash_batch(proxies)
        assert len(ids) == 0  # Should be skipped
        assert skips.get("duplicate_chain") == 1
