import pytest
from unittest.mock import MagicMock
from configstream.intelligence.washer import ProxyWasher
from configstream.intelligence.chaining import generate_smart_chains
from configstream.models import Proxy
from configstream.pipeline_core.stats import PipelineStats


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

@pytest.fixture
def stats():
    return PipelineStats()

@pytest.fixture
def washer_stats_fixture():
    # Setup washer with fake keys so washing actually attempts something
    fake_keys = '[{"private_key": "pk1", "peer_public_key": "pub1", "id": "k1"}]'
    return ProxyWasher(fake_keys)

def test_wash_failed_stats_increment(washer_stats_fixture, stats):
    """Verify wash_failed increments attempts, not revived counts."""
    failed_proxy = Proxy(
        source="test", address="1.1.1.1", port=80, protocol="vmess",
        uuid="fail1", config="...", is_working=False
    )

    # Mock _get_clean_endpoint and _get_consistent_exit to ensure success path
    washer_stats_fixture._get_clean_endpoint = MagicMock(return_value=("1.1.1.1", 2408))

    # 1. Use Vwarp
    cands, count = washer_stats_fixture.wash_failed([failed_proxy], stats=stats, use_vwarp=True)
    assert count == 1
    assert stats.vwarp_attempts == 1
    assert stats.revived_vwarp == 0  # Should NOT increment yet
    assert stats.revived_warp == 0

    # 2. Use Standard Warp
    cands, count = washer_stats_fixture.wash_failed([failed_proxy], stats=stats, use_vwarp=False)
    assert count == 1
    assert stats.warp_attempts == 1
    assert stats.revived_warp == 0  # Should NOT increment yet
    assert stats.revived_vwarp == 0


def test_wash_batch_stats_increment(washer_stats_fixture, stats):
    """Verify wash_batch increments vwarp_attempts/success, but NOT revived_warp."""
    working_proxy = Proxy(
        source="test", address="2.2.2.2", port=80, protocol="vmess",
        uuid="work1", config="...", is_working=True
    )

    # Mock helpers
    washer_stats_fixture._get_clean_endpoint = MagicMock(return_value=("2.2.2.2", 2408))

    outbounds, ids, skips = washer_stats_fixture.wash_batch([working_proxy], stats=stats)

    assert len(outbounds) > 0
    assert stats.vwarp_attempts == 1
    assert stats.vwarp_success == 1
    assert stats.revived_warp == 0  # Should NOT increment
