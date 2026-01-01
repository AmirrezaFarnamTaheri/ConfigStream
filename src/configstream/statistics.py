# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean, median, stdev
from typing import Dict, List, Mapping, Sequence, Any

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
        latencies = [
            proxy.latency
            for proxy in self.proxies
            if proxy.latency is not None
            and 0 < proxy.latency < 5000  # [FIX] Exclude timeouts/outliers
        ]
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

    def detailed_stats(self) -> Dict[str, Any]:
        """Calculate detailed aggregations for analytics charts."""
        lat_by_proto: Dict[str, List[float]] = {}
        lat_by_country: Dict[str, List[float]] = {}

        for p in self.proxies:
            if not p.is_working or p.latency is None:
                continue

            # Protocol
            if p.protocol not in lat_by_proto:
                lat_by_proto[p.protocol] = []
            lat_by_proto[p.protocol].append(p.latency)

            # Country
            cc = p.country_code or "XX"
            if cc not in lat_by_country:
                lat_by_country[cc] = []
            lat_by_country[cc].append(p.latency)

        return {
            "latency_by_protocol": {
                k: int(sum(v) / len(v)) for k, v in lat_by_proto.items() if v
            },
            "latency_by_country": {
                k: int(sum(v) / len(v)) for k, v in lat_by_country.items() if v
            },
        }

    def generate_report(self, stats_obj=None) -> Dict[str, object]:
        uptime = self.uptime_stats()
        report: Dict[str, object] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_proxies": len(self.proxies),
            "working_proxies": uptime.working,
            "success_rate": round(uptime.success_rate * 100, 2),
            "protocol_distribution": dict(self.protocol_distribution()),
            "country_distribution": dict(self.country_distribution()),
            "latency": self.latency_stats(),
        }
        # Inject detailed stats
        report.update(self.detailed_stats())

        # Inject Drop/Threat Reasons from PipelineStats if available
        if stats_obj and hasattr(stats_obj, "drop_reasons"):
            report["rejection_reasons"] = stats_obj.drop_reasons

        return report
