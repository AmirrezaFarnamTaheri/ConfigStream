# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import List, Optional
import logging
from configstream.models import Proxy
from configstream.history.tracker import ProxyHistoryTracker

logger = logging.getLogger(__name__)


def sort_proxies_pareto(
    proxies: List[Proxy], history: Optional[ProxyHistoryTracker] = None
) -> None:
    """
    Sorts proxies in-place using comprehensive health scoring.
    """

    if not proxies:
        logger.warning("No proxies to sort")
        return

    # Pre-fetch stats
    bulk_stats = {}
    if history:
        proxy_ids = [p.id for p in proxies]
        bulk_stats = history.get_bulk_stats(proxy_ids)

    def scoring_key(p: Proxy) -> float:
        # Higher health score (0-100) is better. Sort expects ascending?
        # If we want best first, we sort by negative score.

        # 1. Latency (Lower is better)
        latency = p.latency if p.latency else 9999

        # 2. History Reliability (Higher is better)
        stats = bulk_stats.get(p.id, {})
        reliability = stats.get("reliability", 0.5)  # 0.0 to 1.0

        # 3. Uptime
        uptime = stats.get("uptime", 50.0) / 100.0  # 0.0 to 1.0

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
