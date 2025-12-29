from typing import List
import logging
from configstream.models import Proxy
from configstream.history.tracker import ProxyHistoryTracker

logger = logging.getLogger(__name__)


def sort_proxies_pareto(proxies: List[Proxy], history: ProxyHistoryTracker) -> None:
    """
    Sorts proxies in-place using a Pareto-like scoring system.
    Latency (50%), Reliability/Uptime (30%), Success (20%)
    """

    # Pre-fetch stats to avoid N+1 lookups
    # [OPTIMIZATION] Bulk fetch history stats
    proxy_ids = [p.id for p in proxies]
    bulk_stats = history.get_bulk_stats(proxy_ids)

    def pareto_score(p: Proxy) -> float:
        # Lower score is better
        latency = p.latency if p.latency else 9999

        # Normalize latency: 0-1000ms -> 0-1. Clamp at 1 (1s+)
        norm_latency = min(latency / 1000.0, 1.0)

        # Retrieve pre-calculated stats
        stats = bulk_stats.get(p.id, {})
        reliability = stats.get("reliability", 0.5)
        # Uptime is already a float 0-100 from bulk_stats
        uptime = stats.get("uptime", 50.0) / 100.0

        # Weighted Score
        # Latency: 50%
        # Reliability (History Success): 30%
        # Stability (Uptime): 20%

        score = (
            (norm_latency * 0.5) + ((1.0 - reliability) * 0.3) + ((1.0 - uptime) * 0.2)
        )
        return float(score)

    # Calculate statistics before sorting
    if proxies:
        latencies = [p.latency for p in proxies if p.latency]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0

        proxies.sort(key=pareto_score)

        # Log sorting statistics
        logger.info(
            f"Sorted {len(proxies)} proxies using Pareto scoring "
            f"(latency: avg={avg_latency:.1f}ms, min={min_latency:.1f}ms, max={max_latency:.1f}ms)"
        )
    else:
        logger.warning("No proxies to sort")
