"""Tests for the proxy selection logic."""

import pytest
from configstream.models import Proxy
from configstream.selection import select_chosen_proxies, get_selection_stats

# Helper to create a test proxy
def create_test_proxy(protocol: str, latency: float, working: bool = True) -> Proxy:
    return Proxy(
        config=f"{protocol}://test-{latency}",
        protocol=protocol,
        address="1.2.3.4",
        port=443,
        uuid=f"uuid-{protocol}-{latency}",
        latency=latency,
        is_working=working,
    )

def test_select_chosen_proxies_empty_input():
    """Ensure it handles an empty list without errors."""
    assert select_chosen_proxies([]) == []

def test_select_chosen_proxies_basic_selection():
    """Test it selects top proxies per protocol and fills globally."""
    proxies = [
        create_test_proxy("vmess", 100),
        create_test_proxy("vmess", 50),  # Best vmess
        create_test_proxy("vless", 200),
        create_test_proxy("vless", 150), # Best vless
        create_test_proxy("trojan", 80),  # Best overall
    ]
    # top_per_protocol is 40 by default, so it should take all of them
    chosen = select_chosen_proxies(proxies, top_per_protocol=1, total_limit=3)

    # It should select the best of each protocol first.
    # Then it will fill with the next best globally.
    assert len(chosen) == 3

    chosen_latencies = {p.latency for p in chosen}
    assert 50 in chosen_latencies
    assert 150 in chosen_latencies
    assert 80 in chosen_latencies


def test_select_chosen_proxies_total_limit():
    """Ensure the total_limit is respected."""
    proxies = [create_test_proxy("vmess", i) for i in range(2000)]
    chosen = select_chosen_proxies(proxies, total_limit=500)
    assert len(chosen) == 500

def test_select_chosen_proxies_deduplication():
    """Ensure duplicates are handled correctly."""
    proxies = [
        create_test_proxy("vmess", 100),
        create_test_proxy("vmess", 100),  # Duplicate
        create_test_proxy("vless", 200),
    ]
    chosen = select_chosen_proxies(proxies)
    assert len(chosen) == 2  # Should remove the duplicate

def test_get_selection_stats():
    """Test the statistics generation for the selection."""
    all_proxies = [
        create_test_proxy("vmess", 100),
        create_test_proxy("vless", 200),
        create_test_proxy("trojan", 300, working=False), # one not working
    ]
    chosen_proxies = all_proxies[:2]  # Assume first two were chosen

    stats = get_selection_stats(all_proxies, chosen_proxies)

    assert stats["total_pool"] == 3
    assert stats["selected_count"] == 2
    assert "selection_ratio" in stats

