# SPDX-License-Identifier: AGPL-3.0-or-later
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
    """Collects and emits performance metrics to a file.

    [FIX] Changed from overwrite ('w') to append ('a') mode to preserve
    metrics across batches. Added clear() to prevent memory leaks.
    """

    def __init__(self, output_path: Path):
        self._output_path = output_path
        self._metrics: List[HostMetrics] = []

    def record(self, metrics: HostMetrics) -> None:
        """Record a new metric for a host."""
        self._metrics.append(metrics)

    def write_metrics(self) -> None:
        """Write the collected metrics to the output file in JSONL format."""
        if not self._metrics:
            return
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        # [FIX] Append mode preserves data from previous batches
        with self._output_path.open("a") as f:
            for metric in self._metrics:
                f.write(json.dumps(asdict(metric)) + "\n")
        # [FIX] Clear buffer after writing to prevent memory leak
        self._metrics.clear()
