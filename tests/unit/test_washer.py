import pytest
from configstream.intelligence.washer import ProxyWasher, generate_smart_chains
from configstream.models import Proxy


@pytest.mark.asyncio
async def test_washer_initialization():
    washer = ProxyWasher("[]")
    assert washer is not None


def test_deterministic_warp_keys():
    """Test that the same relay ID produces the same WARP key (deterministic washing)."""
    # Create a washer with some fake keys
    fake_keys = (
        '[{"private_key": "key1", "id": "01"}, {"private_key": "key2", "id": "02"}]'
    )
    washer = ProxyWasher(fake_keys)

    relay_id = "test-relay-id"
    exit1 = washer._get_consistent_exit(relay_id, washer.warp_keys)
    exit2 = washer._get_consistent_exit(relay_id, washer.warp_keys)

    assert exit1 == exit2
    assert exit1["private_key"] in ["key1", "key2"]


@pytest.mark.asyncio
async def test_smart_chain_generation():
    """Test the smart chain logic (Intranet Bridge, IPv6 Portal)."""
    # Create dummy proxies
    proxies = [
        Proxy(
            source="test",
            address="1.1.1.1",
            port=443,
            protocol="vless",
            country_code="IR",
            config="vless://...",
            is_working=True,
            tags=[],
        ),
        Proxy(
            source="test",
            address="2.2.2.2",
            port=443,
            protocol="vless",
            country_code="US",
            config="vless://...",
            is_working=True,
            tags=[],
        ),
    ]

    # Use the standalone function as imported in output.py (or from intelligence.washer)
    chains = generate_smart_chains(proxies)
    # 1.1.1.1 is IR, 2.2.2.2 is US (foreign)
    # Logic: for relay in relays_ir (1.1.1.1) ... for exit in proxies (2.2.2.2) ...
    # It should create a chain
    assert "intranet" in chains
    assert len(chains["intranet"]) > 0
