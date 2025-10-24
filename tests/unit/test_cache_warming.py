"""Tests for cache warming functionality."""

import pytest
from configstream.cache_warming import warm_cache, get_cache_warming_strategy
from configstream.test_cache import TestResultCache
from configstream.models import Proxy


@pytest.fixture
def test_cache(tmp_path):
    """Create a test cache."""
    cache_path = tmp_path / "test_cache.db"
    return TestResultCache(db_path=str(cache_path))


@pytest.fixture
def sample_proxies():
    """Create sample proxies for testing."""
    return [
        Proxy(
            config=f"vmess://test{i}",
            protocol="vmess",
            address=f"1.2.3.{i}",
            port=443,
            is_working=True,
            latency=100 + i * 10,
        )
        for i in range(10)
    ]


def test_warm_cache_prioritizes_high_quality(test_cache, sample_proxies):
    """Test that cache warming prioritizes high-quality proxies."""
    # Add some proxies to cache with different health scores
    for i, proxy in enumerate(sample_proxies[:5]):
        test_cache.set(proxy)
        # Simulate different success rates
        if i < 2:
            # High quality - 100% success (>70% threshold)
            for _ in range(10):
                test_cache.set(proxy)
        elif i < 4:
            # Medium quality - 50% success (<70% threshold)
            for _ in range(5):
                test_cache.set(proxy)
            failed_proxy = Proxy(
                config=proxy.config,
                protocol=proxy.protocol,
                address=proxy.address,
                port=proxy.port,
                is_working=False,
            )
            for _ in range(5):
                test_cache.set(failed_proxy)

    # Warm the cache
    warmed = warm_cache(test_cache, sample_proxies)

    # Verify all proxies are returned
    assert len(warmed) == len(sample_proxies)

    # Verify all proxies are present
    warmed_configs = set(p.config for p in warmed)
    original_configs = set(p.config for p in sample_proxies)
    assert warmed_configs == original_configs


def test_warm_cache_with_no_cached_proxies(test_cache, sample_proxies):
    """Test cache warming with no cached proxies."""
    warmed = warm_cache(test_cache, sample_proxies)

    # All proxies should be in uncached category
    assert len(warmed) == len(sample_proxies)
    assert set(p.config for p in warmed) == set(p.config for p in sample_proxies)


def test_warm_cache_with_all_cached_proxies(test_cache, sample_proxies):
    """Test cache warming with all proxies cached."""
    # Cache all proxies
    for proxy in sample_proxies:
        for _ in range(10):  # High success rate
            test_cache.set(proxy)

    warmed = warm_cache(test_cache, sample_proxies)

    # All proxies should be in high-quality category
    assert len(warmed) == len(sample_proxies)


def test_warm_cache_with_empty_list(test_cache):
    """Test cache warming with empty proxy list."""
    warmed = warm_cache(test_cache, [])
    assert warmed == []


def test_get_cache_warming_strategy_small():
    """Test cache warming strategy for small proxy count."""
    strategy = get_cache_warming_strategy(50)
    assert strategy["priority_test_count"] == 50
    assert strategy["batch_size"] == 50


def test_get_cache_warming_strategy_medium():
    """Test cache warming strategy for medium proxy count."""
    strategy = get_cache_warming_strategy(500)
    assert strategy["priority_test_count"] == 100
    assert strategy["batch_size"] == 100


def test_get_cache_warming_strategy_large():
    """Test cache warming strategy for large proxy count."""
    strategy = get_cache_warming_strategy(2000)
    assert strategy["priority_test_count"] == 200
    assert strategy["batch_size"] == 200


def test_warm_cache_ordering_correctness(test_cache, sample_proxies):
    """Test that cache warming maintains correct ordering."""
    # Create proxies with different quality levels
    high_quality = sample_proxies[0]
    medium_quality = sample_proxies[1]
    uncached = sample_proxies[2]

    # Set high quality (90% success > 70% threshold)
    for _ in range(9):
        test_cache.set(high_quality)
    failed = Proxy(
        config=high_quality.config,
        protocol=high_quality.protocol,
        address=high_quality.address,
        port=high_quality.port,
        is_working=False,
    )
    test_cache.set(failed)

    # Set medium quality (60% success < 70% threshold)
    for _ in range(6):
        test_cache.set(medium_quality)
    failed2 = Proxy(
        config=medium_quality.config,
        protocol=medium_quality.protocol,
        address=medium_quality.address,
        port=medium_quality.port,
        is_working=False,
    )
    for _ in range(4):
        test_cache.set(failed2)

    warmed = warm_cache(test_cache, [high_quality, medium_quality, uncached])

    # Verify ordering: high quality first (>70%), then uncached, then medium quality (<=70%)
    assert len(warmed) == 3

    # Check that high quality proxy comes before medium quality
    high_idx = next(i for i, p in enumerate(warmed) if p.config == high_quality.config)
    med_idx = next(i for i, p in enumerate(warmed) if p.config == medium_quality.config)
    assert high_idx < med_idx  # High quality should come before medium quality
