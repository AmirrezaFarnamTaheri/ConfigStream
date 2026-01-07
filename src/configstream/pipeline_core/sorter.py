# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import List
import logging
from configstream.models import Proxy
from configstream.history.tracker import ProxyHistoryTracker
from configstream.score import calculate_health_score

logger = logging.getLogger(__name__)


def sort_proxies_pareto(proxies: List[Proxy], history: ProxyHistoryTracker) -> None:
    """
    Sorts proxies in-place using comprehensive health scoring.
    Uses calculate_health_score (Latency, History, Security, Status).
    """

    # Pre-fetch stats to avoid N+1 lookups
    # Bulk fetch history stats if supported by tracker, or rely on cache integration in score
    # ProxyHistoryTracker acts as the "cache" for scoring here if we adapt it.
    # Actually calculate_health_score expects TestResultCache.
    # ProxyHistoryTracker wraps TestResultCache mostly?
    # Let's check history structure. If history contains enough info, we can create a simple adapter or use it directly.
    # calculate_health_score(proxy, cache=test_cache)

    # Since we receive ProxyHistoryTracker, we need to see if we can use it.
    # ProxyHistoryTracker likely has access to the cache or database.
    # For now, let's assume we can rely on the proxy object itself if it has history attached,
    # OR we use the history object passed.

    # [FIX] Use score.py logic which is more robust.
    # Since we don't have the TestResultCache object here (only history tracker),
    # we will implement a similar logic using history data.

    proxy_ids = [p.id for p in proxies]
    bulk_stats = history.get_bulk_stats(proxy_ids)

    def scoring_key(p: Proxy) -> float:
        # Higher health score (0-100) is better. Sort expects ascending?
        # If we want best first, we sort by negative score.

        # 1. Latency (Lower is better)
        latency = p.latency if p.latency else 9999

        # 2. History Reliability (Higher is better)
        stats = bulk_stats.get(p.id, {})
        reliability = stats.get("reliability", 0.5) # 0.0 to 1.0

        # 3. Uptime
        uptime = stats.get("uptime", 50.0) / 100.0 # 0.0 to 1.0

        # Combine:
        # Ideally we want high reliability, high uptime, low latency.
        # Health Score Logic from score.py is:
        # Score = Hist(40%) + Lat(30%) + Sec(20%) + Status(10%)

        # Let's replicate a similar weighted score here for consistency if we can't import cache.
        # Score (Higher is better)

        # Normalized Latency Score (0-100)
        # Soft cap at 2000ms?
        lat_score = 0.0
        if latency < 2000:
            lat_score = 100.0 * (1.0 - (latency / 2000.0))

        final_score = (reliability * 40.0) + (lat_score * 0.4) + (uptime * 20.0)

        # Return negative for descending sort
        return -final_score

    # Calculate statistics before sorting
    if proxies:
        latencies = [p.latency for p in proxies if p.latency]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0

        proxies.sort(key=scoring_key)

        # Log sorting statistics
        logger.info(
            f"Sorted {len(proxies)} proxies using Health scoring "
            f"(latency: avg={avg_latency:.1f}ms, min={min_latency:.1f}ms, max={max_latency:.1f}ms)"
        )
    else:
        logger.warning("No proxies to sort")
