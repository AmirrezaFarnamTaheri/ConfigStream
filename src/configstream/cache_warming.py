"""
Cache warming functionality to pre-test high-quality proxies.

This module prioritizes testing proxies with known good performance
to ensure the best proxies are always available quickly.
"""

from typing import Any, List
from .models import Proxy
from .test_cache import TestResultCache


def warm_cache(cache: TestResultCache, proxies: List[Proxy]) -> List[Proxy]:
    """
    Warm the cache by prioritizing high-quality proxies for testing.

    Args:
        cache: Test result cache
        proxies: List of proxies to test

    Returns:
        Reordered list with high-quality proxies first
    """
    # Separate proxies by cache status
    cached = []
    uncached = []

    for proxy in proxies:
        if cache.get(proxy):
            cached.append((proxy, cache.get_health_score(proxy)))
        else:
            uncached.append(proxy)

    # Sort cached by health score (highest first)
    cached.sort(key=lambda x: x[1], reverse=True)

    # Return high-quality proxies first, then uncached
    return [p for p, _ in cached if _ > 70] + uncached + [p for p, s in cached if s <= 70]


def get_cache_warming_strategy(total_proxies: int) -> dict[str, Any]:
    """
    Get recommended cache warming strategy based on proxy count.

    Args:
        total_proxies: Total number of proxies to test

    Returns:
        Dictionary with warming strategy parameters
    """
    if total_proxies < 100:
        return {"priority_test_count": total_proxies, "batch_size": 50}
    elif total_proxies < 1000:
        return {"priority_test_count": 100, "batch_size": 100}
    else:
        return {"priority_test_count": 200, "batch_size": 200}
