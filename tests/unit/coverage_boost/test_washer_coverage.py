# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from configstream.models import Proxy
from configstream.intelligence.washer.core import ProxyWasher


@pytest.fixture
def mock_warp_keys():
    return (
        '[{"private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=", '
        '"peer_public_key": "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE=", '
        '"id": "key1"}, '
        '{"private_key": "AgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg=", '
        '"peer_public_key": "AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwM=", '
        '"id": "key2"}]'
    )


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
    # Fallback to checking if it's a valid IP string format or in the expected set
    # Since we added many fallback IPs, strict equality to the default 3 is no longer valid
    assert isinstance(ep, str)
    assert len(ep.split(".")) == 4

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
