"""
Metrics collection and reporting for ConfigStream.

Provides JSON metrics endpoint compatible with zero-budget GitHub Pages deployment.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict


@dataclass
class PipelineMetrics:
    """Container for pipeline execution metrics."""

    # Counters
    total_sources: int = 0
    total_fetched: int = 0
    total_parsed: int = 0
    total_tested: int = 0
    total_working: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    # Timing
    start_time: float = field(default_factory=time.time)
    fetch_duration: float = 0.0
    parse_duration: float = 0.0
    test_duration: float = 0.0
    geo_duration: float = 0.0
    total_duration: float = 0.0

    # Rates
    success_rate: float = 0.0
    cache_hit_rate: float = 0.0
    avg_latency: float = 0.0

    # Protocol distribution
    protocol_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON export."""
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
                "throughput_proxies_per_min": round(
                    self.total_tested / (self.test_duration / 60) if self.test_duration > 0 else 0,
                    2,
                ),
            },
            "protocols": self.protocol_counts,
            "timestamp": time.time(),
        }

    def save_to_file(self, output_path: Path) -> None:
        """Save metrics to JSON file."""
        metrics_file = output_path / "metrics.json"
        with open(metrics_file, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


def export_metrics(metrics: PipelineMetrics, output_path: Path) -> str:
    """
    Export metrics to JSON file for GitHub Pages consumption.

    Args:
        metrics: Pipeline metrics to export
        output_path: Directory to save metrics

    Returns:
        Path to metrics file
    """
    metrics.save_to_file(output_path)
    return str(output_path / "metrics.json")
