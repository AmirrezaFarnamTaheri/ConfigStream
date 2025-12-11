import pytest
from configstream.intelligence.washer import ProxyWasher
from configstream.intelligence.chaining import generate_smart_chains
from configstream.models import Proxy


@pytest.mark.asyncio
async def test_washer_initialization():
    washer = ProxyWasher("[]")
    assert washer is not None


def test_deterministic_warp_keys():
    """Test that the same relay ID produces the same WARP key (deterministic washing)."""
    # Create a washer with some fake keys
    fake_keys = '[{"private_key": "key1", "peer_public_key": "pub1", "id": "01"}, {"private_key": "key2", "peer_public_key": "pub2", "id": "02"}]'
    washer = ProxyWasher(fake_keys)

    relay_id = "test-relay-id"
    exit1 = washer._get_consistent_exit(relay_id, washer.warp_keys)
    exit2 = washer._get_consistent_exit(relay_id, washer.warp_keys)

    assert exit1 == exit2
    assert exit1["private_key"] in ["key1", "key2"]


# Remove async because generate_smart_chains is synchronous
def test_smart_chain_generation():
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
            uuid="00000000-0000-0000-0000-000000000000",
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
            uuid="11111111-1111-1111-1111-111111111111",
            is_working=True,
            tags=[],
        ),
    ]

    # Use the standalone function as imported in output.py (or from intelligence.chaining)
    chains = generate_smart_chains(proxies)
    # 1.1.1.1 is IR, 2.2.2.2 is US (foreign)
    # Logic: for relay in relays_ir (1.1.1.1) ... for exit in proxies (2.2.2.2) ...
    # It should create a chain
    assert "intranet" in chains
    # Chains is Dict[str, List[List[Dict]]]
    assert len(chains["intranet"]) > 0
    assert isinstance(chains["intranet"][0], list)
