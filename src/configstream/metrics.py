# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Metrics collection for ConfigStream.
"""
import json
import time
from dataclasses import dataclass, field
from typing import Dict, Any
from pathlib import Path


@dataclass
class PipelineMetrics:
    """Dataclass to hold pipeline execution metrics."""

    total_sources: int = 0
    total_fetched: int = 0
    total_parsed: int = 0
    total_tested: int = 0
    total_working: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    fetch_duration: float = 0.0
    parse_duration: float = 0.0
    test_duration: float = 0.0
    geo_duration: float = 0.0
    total_duration: float = 0.0

    success_rate: float = 0.0
    cache_hit_rate: float = 0.0
    avg_latency: float = 0.0

    protocol_counts: Dict[str, int] = field(default_factory=dict)

    start_time: float = field(default_factory=time.time)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a dictionary for JSON output."""
        return {
            "counters": {
                "total_sources": self.total_sources,
                "total_fetched": self.total_fetched,
                "total_parsed": self.total_parsed,
                "total_tested": self.total_tested,
                "total_working": self.total_working,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
            },
            "timing": {
                "fetch_duration_sec": round(self.fetch_duration, 2),
                "parse_duration_sec": round(self.parse_duration, 2),
                "test_duration_sec": round(self.test_duration, 2),
                "geo_duration_sec": round(self.geo_duration, 2),
                "total_duration_sec": round(self.total_duration, 2),
            },
            "rates": {
                "success_rate_pct": round(self.success_rate * 100, 2),
                "cache_hit_rate_pct": round(self.cache_hit_rate * 100, 2),
                "average_latency_ms": round(self.avg_latency, 2),
                "throughput_proxies_per_min": self._calculate_throughput(),
            },
            "protocols": self.protocol_counts,
            "timestamp": self.timestamp,
        }

    def _calculate_throughput(self) -> float:
        if self.test_duration > 0:
            # proxies per minute
            return round((self.total_tested / self.test_duration) * 60, 1)
        return 0.0

    def save_to_file(self, output_path: Path):
        """Save metrics to a file."""
        data = self.to_dict()
        file_path = output_path / "metrics.json"

        # Atomic write: write to temp file then rename
        tmp_path = file_path.with_suffix(".json.tmp")
        try:
            with open(tmp_path, "w") as f:
                json.dump(data, f, indent=2)
            tmp_path.replace(file_path)
        except Exception:
            # If replacement fails, try to cleanup tmp file
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            raise


def export_metrics(metrics: PipelineMetrics, output_path: Path) -> str:
    """Export metrics to a file and return the path."""
    metrics.save_to_file(output_path)
    return str(output_path / "metrics.json")
