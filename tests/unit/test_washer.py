# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import MagicMock, patch
from configstream.intelligence.washer.core import ProxyWasher
from configstream.intelligence.chaining import generate_smart_chains
from configstream.models import Proxy
from configstream.pipeline_stats import PipelineStats


@pytest.mark.asyncio
async def test_washer_initialization():
    washer = ProxyWasher("[]")
    assert washer is not None


def test_deterministic_warp_keys():
    """Test that the same relay ID produces the same WARP key (deterministic washing)."""
    # Create a washer with some fake keys
    key_a = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    key_b = "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE="
    fake_keys = (
        f'[{{"private_key": "{key_a}", "peer_public_key": "AgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg=", "id": "01"}}, '
        f'{{"private_key": "{key_b}", "peer_public_key": "AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwM=", "id": "02"}}]'
    )
    washer = ProxyWasher(fake_keys)

    relay_id = "test-relay-id"
    exit1 = washer._get_consistent_exit(relay_id, washer.warp_keys)
    exit2 = washer._get_consistent_exit(relay_id, washer.warp_keys)

    assert exit1 == exit2
    assert exit1["private_key"] in [key_a, key_b]


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
    fake_keys = (
        '[{"private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=", '
        '"peer_public_key": "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE=", '
        '"id": "k1"}]'
    )
    return ProxyWasher(fake_keys)


def test_wash_failed_stats_increment(washer_stats_fixture, stats):
    """Verify wash_failed increments attempts, not revived counts."""
    failed_proxy = Proxy(
        source="test",
        address="1.1.1.1",
        port=80,
        protocol="vmess",
        uuid="fail1",
        config="...",
        is_working=False,
    )

    # Mock _get_clean_endpoint and _get_consistent_exit to ensure success path
    washer_stats_fixture._get_clean_endpoint = MagicMock(return_value=("1.1.1.1", 2408))

    # 1. Use Vwarp
    cands, count = washer_stats_fixture.wash_failed(
        [failed_proxy], stats=stats, use_vwarp=True
    )
    assert count == 1
    assert stats.vwarp_attempts == 1
    assert stats.revived_vwarp == 0  # Should NOT increment yet
    assert stats.revived_warp == 0

    # 2. Use Standard Warp
    cands, count = washer_stats_fixture.wash_failed(
        [failed_proxy], stats=stats, use_vwarp=False
    )
    assert count == 1
    assert stats.warp_attempts == 1
    assert stats.revived_warp == 0  # Should NOT increment yet
    assert stats.revived_vwarp == 0


def test_wash_batch_stats_increment(washer_stats_fixture, stats):
    """Verify wash_batch increments warp attempts and success count."""
    working_proxy = Proxy(
        source="test",
        address="2.2.2.2",
        port=80,
        protocol="vmess",
        uuid="work1",
        config="...",
        is_working=True,
    )

    # Mock helpers
    washer_stats_fixture._get_clean_endpoint = MagicMock(return_value=("2.2.2.2", 2408))

    outbounds, ids, skips = washer_stats_fixture.wash_batch(
        [working_proxy], stats=stats
    )

    assert len(outbounds) > 0
    assert stats.warp_attempts == 1
    assert stats.washer_success_count == 1
    assert stats.revived_warp == 0  # Should NOT increment


def test_shield_batch_does_not_mutate_source_proxy_state(washer_stats_fixture):
    """Shielding metadata must stay on outbounds and not overwrite source proxy labels."""
    dead_proxy = Proxy(
        source="test",
        address="1.1.1.1",
        port=443,
        protocol="vless",
        uuid="123e4567-e89b-12d3-a456-426614174000",
        config="vless://123e4567-e89b-12d3-a456-426614174000@1.1.1.1:443?security=tls&sni=example.com#dead",
        is_working=False,
        process="revived-warp",
        details={"is_revived": True},
    )

    washer_stats_fixture.get_warp_config = MagicMock(
        return_value={
            "type": "wireguard",
            "tag": "wg-shield",
            "server": "162.159.192.1",
            "server_port": 2408,
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "peer_public_key": "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE=",
            "local_address": ["10.0.0.2/32"],
            "mtu": 1280,
        }
    )

    with patch(
        "configstream.intelligence.washer.core.to_singbox_outbound",
        return_value={"type": "vless", "tag": "relay", "server": "1.1.1.1", "server_port": 443},
    ):
        outbounds, ids = washer_stats_fixture.shield_batch([dead_proxy])

    assert dead_proxy.process == "revived-warp"
    assert "is_shielded" not in dead_proxy.details
    assert dead_proxy.details.get("is_revived") is True
    assert dead_proxy.id in ids
    assert any(ob.get("_is_shielded") is True for ob in outbounds)
