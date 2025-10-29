from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List


@dataclass
class HostMetrics:
    """Dataclass for storing metrics for a single host."""

    host: str
    p50_latency: float
    p95_latency: float
    error_rate: float
    concurrency_limit: int


class MetricsEmitter:
    """Collects and emits performance metrics to a file."""

    def __init__(self, output_path: Path):
        self._output_path = output_path
        self._metrics: List[HostMetrics] = []

    def record(self, metrics: HostMetrics) -> None:
        """Record a new metric for a host."""
        self._metrics.append(metrics)

    def write_metrics(self) -> None:
        """Write the collected metrics to the output file in JSONL format."""
        with self._output_path.open("w") as f:
            for metric in self._metrics:
                f.write(json.dumps(asdict(metric)) + "\n")
