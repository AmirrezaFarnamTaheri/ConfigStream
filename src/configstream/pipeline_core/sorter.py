from typing import List
from ..models import Proxy
from ..proxy_history import ProxyHistoryTracker


def sort_proxies_pareto(proxies: List[Proxy], history: ProxyHistoryTracker) -> None:
    """
    Sorts proxies in-place using a Pareto-like scoring system.
    Latency (50%), Reliability/Uptime (30%), Success (20%)
    """

    def pareto_score(p: Proxy) -> float:
        # Lower score is better
        latency = p.latency if p.latency else 9999

        # Normalize latency: 0-1000ms -> 0-1. Clamp at 1 (1s+)
        norm_latency = min(latency / 1000.0, 1.0)

        # Reliability (Success Rate) from History
        # Note: get_reliability_score returns 0-1 (higher is better)
        # We invert it so lower is better (1 - score)
        reliability = history.get_reliability_score(p.id)

        # Stability (Jitter)
        # We use uptime_percentage from summary as 'stability' proxy if available
        summary = history.get_summary_stats(p.id)
        uptime = summary.get("uptime_percentage", 50.0) / 100.0

        # Weighted Score
        # Latency: 50%
        # Reliability (History Success): 30%
        # Stability (Uptime): 20%

        score = (
            (norm_latency * 0.5) + ((1.0 - reliability) * 0.3) + ((1.0 - uptime) * 0.2)
        )
        return float(score)

    proxies.sort(key=pareto_score)
