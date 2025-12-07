"""
Performance Metrics Logger
Provides structured logging for pipeline performance analysis and optimization.
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from typing import Optional
import json

logger = logging.getLogger(__name__)


@dataclass
class BatchMetrics:
    """Metrics for a single batch execution."""

    batch_number: int
    sources_count: int
    proxies_fetched: int
    proxies_tested: int
    proxies_working: int
    duration_seconds: float
    throughput_proxies_per_sec: float
    success_rate: float
    fetch_failures: int
    test_failures: int


@dataclass
class ReshardingMetrics:
    """Metrics for source distribution optimization."""

    total_sources: int
    sources_from_logs: int
    sources_with_default_weight: int
    batches_count: int
    load_balance_ratio: float  # max_load / min_load
    std_deviation: float
    heaviest_batch_load: int
    lightest_batch_load: int


@dataclass
class PipelineMetrics:
    """Overall pipeline execution metrics."""

    total_duration_seconds: float
    total_proxies_fetched: int
    total_proxies_working: int
    total_threats_blocked: int
    total_revived: int
    batches_completed: int
    overall_success_rate: float
    avg_batch_duration: float


class PerformanceLogger:
    """
    Structured logger for performance metrics with JSON export capability.
    """

    def __init__(self, output_file: Optional[str] = None):
        self.output_file = output_file
        self.metrics_buffer = []

    @contextmanager
    def measure_batch(self, batch_number: int):
        """
        Context manager to measure batch execution time.

        Usage:
            with perf_logger.measure_batch(1) as metrics:
                # ... execute batch ...
                metrics['proxies_fetched'] = 100
        """
        start_time = time.time()
        metrics = {
            "batch_number": batch_number,
            "sources_count": 0,
            "proxies_fetched": 0,
            "proxies_tested": 0,
            "proxies_working": 0,
            "fetch_failures": 0,
            "test_failures": 0,
        }

        try:
            yield metrics
        finally:
            duration = time.time() - start_time
            metrics["duration_seconds"] = round(duration, 2)

            # Calculate derived metrics
            if duration > 0:
                metrics["throughput_proxies_per_sec"] = round(
                    metrics["proxies_tested"] / duration, 2
                )
            else:
                metrics["throughput_proxies_per_sec"] = 0.0

            if metrics["proxies_tested"] > 0:
                metrics["success_rate"] = round(
                    metrics["proxies_working"] / metrics["proxies_tested"], 4
                )
            else:
                metrics["success_rate"] = 0.0

            batch_metrics = BatchMetrics(**metrics)
            self.log_batch_metrics(batch_metrics)

    def log_batch_metrics(self, metrics: BatchMetrics):
        """Log batch metrics in structured format."""
        logger.info(
            f"[PERF] Batch {metrics.batch_number} completed: "
            f"{metrics.proxies_working}/{metrics.proxies_tested} working "
            f"({metrics.success_rate:.1%}), "
            f"{metrics.duration_seconds}s "
            f"({metrics.throughput_proxies_per_sec:.1f} proxies/s)"
        )

        # Buffer for JSON export
        self.metrics_buffer.append(
            {"type": "batch", "timestamp": time.time(), "data": asdict(metrics)}
        )

    def log_resharding_metrics(self, metrics: ReshardingMetrics):
        """Log resharding optimization results."""
        logger.info(
            f"[PERF] Resharding optimized: "
            f"{metrics.total_sources} sources → {metrics.batches_count} batches, "
            f"balance={metrics.load_balance_ratio:.2f}x, "
            f"std_dev={metrics.std_deviation:.1f}"
        )

        self.metrics_buffer.append(
            {"type": "resharding", "timestamp": time.time(), "data": asdict(metrics)}
        )

    def log_pipeline_metrics(self, metrics: PipelineMetrics):
        """Log overall pipeline execution summary."""
        logger.info(
            f"[PERF] Pipeline completed: "
            f"{metrics.total_proxies_working}/{metrics.total_proxies_fetched} working "
            f"({metrics.overall_success_rate:.1%}), "
            f"duration={metrics.total_duration_seconds:.1f}s, "
            f"{metrics.batches_completed} batches, "
            f"avg_batch={metrics.avg_batch_duration:.1f}s"
        )

        self.metrics_buffer.append(
            {"type": "pipeline", "timestamp": time.time(), "data": asdict(metrics)}
        )

    def export_metrics(self, filepath: Optional[str] = None):
        """Export collected metrics to JSON file."""
        output = filepath or self.output_file
        if not output:
            logger.warning("No output file specified for metrics export")
            return

        try:
            with open(output, "w") as f:
                json.dump(self.metrics_buffer, f, indent=2)
            logger.info(f"Exported {len(self.metrics_buffer)} metrics to {output}")
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")


# Global instance for easy access
performance_logger = PerformanceLogger()
