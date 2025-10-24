"""Tests for test result caching system."""

import tempfile
from pathlib import Path

import pytest

from configstream.models import Proxy
from configstream.test_cache import TestResultCache


@pytest.fixture
def temp_cache():
    """Create a temporary test cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = TestResultCache(db_path=str(Path(tmpdir) / "test.db"), ttl_seconds=60)
        yield cache


@pytest.fixture
def sample_proxy():
    """Create a sample proxy for testing."""
    return Proxy(
        config="vmess://test123",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        uuid="test-uuid",
        is_working=True,
        latency=100.5,
        country="US",
        country_code="US",
        city="New York",
    )


def test_cache_init(temp_cache):
    """Test cache initialization."""
    assert temp_cache.ttl_seconds == 60
    assert temp_cache.db_path.exists()


def test_cache_set_and_get(temp_cache, sample_proxy):
    """Test setting and getting cached results."""
    # Initially no cache
    assert temp_cache.get(sample_proxy) is None

    # Set cache
    temp_cache.set(sample_proxy)

    # Should retrieve from cache
    cached = temp_cache.get(sample_proxy)
    assert cached is not None
    assert cached.is_working is True
    assert cached.latency == 100.5
    assert cached.country == "US"


def test_cache_ttl_expiration(temp_cache, sample_proxy):
    """Test cache TTL expiration."""
    # Create cache with 0 second TTL
    cache_no_ttl = TestResultCache(db_path=temp_cache.db_path, ttl_seconds=0)

    cache_no_ttl.set(sample_proxy)

    # Should be expired immediately
    assert cache_no_ttl.get(sample_proxy) is None


def test_health_score(temp_cache, sample_proxy):
    """Test health score calculation."""
    # Initially neutral score
    score = temp_cache.get_health_score(sample_proxy)
    assert score == 0.5

    # Add successful test
    sample_proxy.is_working = True
    temp_cache.set(sample_proxy)

    score = temp_cache.get_health_score(sample_proxy)
    assert score == 1.0  # 100% success rate

    # Add failed test
    sample_proxy.is_working = False
    temp_cache.set(sample_proxy)

    score = temp_cache.get_health_score(sample_proxy)
    assert score == 0.5  # 50% success rate (1 success, 1 failure)


def test_cache_stats(temp_cache, sample_proxy):
    """Test cache statistics."""
    # Initially empty
    stats = temp_cache.get_stats()
    assert stats["total_entries"] == 0
    assert stats["valid_entries"] == 0

    # Add entry
    temp_cache.set(sample_proxy)

    stats = temp_cache.get_stats()
    assert stats["total_entries"] == 1
    assert stats["valid_entries"] == 1


def test_cleanup_expired(temp_cache, sample_proxy):
    """Test cleanup of expired entries."""
    # Create cache with 0 TTL
    cache = TestResultCache(db_path=temp_cache.db_path, ttl_seconds=0)

    cache.set(sample_proxy)

    # Should remove expired entry
    removed = cache.cleanup_expired()
    assert removed == 1

    stats = cache.get_stats()
    assert stats["total_entries"] == 0


def test_empty_config_handling(temp_cache):
    """Test handling of proxies with empty config."""
    proxy = Proxy(config="", protocol="vmess", address="1.2.3.4", port=443)

    # Should not cache empty configs
    temp_cache.set(proxy)
    assert temp_cache.get(proxy) is None
