"""Tests for the proxy selection logic."""

import pytest
from configstream.models import Proxy
from configstream.selection import select_chosen_proxies, get_selection_stats
from configstream.constants import CHOSEN_TOP_PER_PROTOCOL, CHOSEN_TOTAL_TARGET


def create_test_proxy(
    protocol: str, latency: float, working: bool = True, security_issues: dict = None
) -> Proxy:
    """Helper to create test proxy."""
    return Proxy(
        config=f"{protocol}://test",
        protocol=protocol,
        address="1.2.3.4",
        port=443,
        uuid=f"test-{protocol}-{latency}",
        latency=latency,
        is_working=working,
        security_issues=security_issues or {},
    )


def test_select_chosen_empty_list():
    """Test selection with empty list."""
    chosen = select_chosen_proxies([])
    assert chosen == []


def test_select_chosen_all_broken():
    """Test selection when all proxies are broken."""
    proxies = [
        create_test_proxy("vmess", 100, working=False),
        create_test_proxy("vless", 200, working=False),
    ]
    chosen = select_chosen_proxies(proxies)
    assert chosen == []


def test_select_chosen_with_security_issues():
    """Test that proxies with security issues are excluded."""
    proxies = [
        create_test_proxy("vmess", 100),
        create_test_proxy("vless", 200, security_issues={"port_security": ["Unsafe port"]}),
        create_test_proxy("trojan", 300),
    ]
    chosen = select_chosen_proxies(proxies)
    assert len(chosen) == 2
    assert all(p.protocol in ["vmess", "trojan"] for p in chosen)


def test_select_chosen_top_per_protocol():
    """Test that top N per protocol are selected."""
    # Create 50 vmess proxies (should select top 40)
    proxies = [create_test_proxy("vmess", i * 10) for i in range(50)]
    # Add 50 vless proxies
    proxies.extend([create_test_proxy("vless", i * 10) for i in range(50)])

    chosen = select_chosen_proxies(proxies)

    # Count by protocol
    vmess_count = sum(1 for p in chosen if p.protocol == "vmess")
    vless_count = sum(1 for p in chosen if p.protocol == "vless")

    assert vmess_count == CHOSEN_TOP_PER_PROTOCOL
    assert vless_count == CHOSEN_TOP_PER_PROTOCOL


def test_select_chosen_fills_to_target():
    """Test that selection fills to target from all protocols."""
    # Create 30 of each protocol (total 90)
    # Should select all 90 since it's less than 1000
    protocols = ["vmess", "vless", "trojan"]
    proxies = []
    for proto in protocols:
        proxies.extend([create_test_proxy(proto, i * 10) for i in range(30)])

    chosen = select_chosen_proxies(proxies)
    assert len(chosen) == 90  # All should be selected


def test_select_chosen_respects_limit():
    """Test that selection doesn't exceed CHOSEN_TOTAL_TARGET."""
    # Create 2000 proxies (should select 1000)
    proxies = [create_test_proxy("vmess", i) for i in range(2000)]

    chosen = select_chosen_proxies(proxies)
    assert len(chosen) == CHOSEN_TOTAL_TARGET


def test_select_chosen_sorted_by_latency():
    """Test that chosen proxies are sorted by latency."""
    proxies = [
        create_test_proxy("vmess", 500),
        create_test_proxy("vless", 100),
        create_test_proxy("trojan", 300),
    ]

    chosen = select_chosen_proxies(proxies)
    latencies = [p.latency for p in chosen]
    assert latencies == sorted(latencies)


def test_get_selection_stats():
    """Test selection statistics generation."""
    proxies = [
        create_test_proxy("vmess", 100),
        create_test_proxy("vmess", 200),
        create_test_proxy("vless", 150),
        create_test_proxy("trojan", 300, working=False),
    ]

    chosen = select_chosen_proxies(proxies)
    stats = get_selection_stats(proxies, chosen)

    assert stats["total_tested"] == 4
    assert stats["working"] == 3
    assert stats["chosen_count"] == 3
    assert stats["protocols_represented"] == 2
    assert "by_protocol_chosen" in stats
    assert "avg_latency_ms" in stats


def test_select_chosen_protocol_diversity():
    """Test that selection maintains protocol diversity."""
    # Create 100 vmess and 10 vless
    proxies = [create_test_proxy("vmess", i) for i in range(100)]
    proxies.extend([create_test_proxy("vless", i) for i in range(10)])

    chosen = select_chosen_proxies(proxies)

    # Both protocols should be represented
    vmess_count = sum(1 for p in chosen if p.protocol == "vmess")
    vless_count = sum(1 for p in chosen if p.protocol == "vless")

    assert vless_count == 10  # All vless should be included
    assert vmess_count == CHOSEN_TOP_PER_PROTOCOL  # Top 40 vmess
