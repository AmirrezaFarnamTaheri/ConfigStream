from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean, median, stdev
from typing import Dict, List, Mapping, Sequence

from .models import Proxy


@dataclass
class UptimeStats:
    total_tested: int
    working: int

    @property
    def success_rate(self) -> float:
        if self.total_tested == 0:
            return 0.0
        return self.working / self.total_tested


class StatisticsEngine:
    """Compute aggregate statistics for a collection of proxies."""

    def __init__(self, proxies: Sequence[Proxy]):
        self.proxies: List[Proxy] = list(proxies)

    def protocol_distribution(self) -> Mapping[str, int]:
        return Counter(proxy.protocol for proxy in self.proxies)

    def country_distribution(self) -> Mapping[str, int]:
        return Counter(proxy.country or "Unknown" for proxy in self.proxies)

    def latency_stats(self) -> Dict[str, float]:
        latencies = [proxy.latency for proxy in self.proxies if proxy.latency is not None]
        if not latencies:
            return {}
        stats: Dict[str, float] = {
            "min": min(latencies),
            "max": max(latencies),
            "mean": mean(latencies),
            "median": median(latencies),
        }
        if len(latencies) > 1:
            stats["stdev"] = stdev(latencies)
        else:
            stats["stdev"] = 0.0
        return stats

    def uptime_stats(self) -> UptimeStats:
        total = len(self.proxies)
        working = sum(1 for proxy in self.proxies if proxy.is_working)
        return UptimeStats(total_tested=total, working=working)

    def generate_report(self) -> Dict[str, object]:
        uptime = self.uptime_stats()
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_proxies": len(self.proxies),
            "working_proxies": uptime.working,
            "success_rate": round(uptime.success_rate * 100, 2),
            "protocol_distribution": dict(self.protocol_distribution()),
            "country_distribution": dict(self.country_distribution()),
            "latency": self.latency_stats(),
        }
