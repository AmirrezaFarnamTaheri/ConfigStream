# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Adaptive Timeout Mechanism.
Dynamically adjusts socket timeouts based on network conditions.
"""

import asyncio
import logging
import statistics
import json
from pathlib import Path
from collections import defaultdict

from .security_validator import SecurityValidator
from .utils import AtomicFileWriter

logger = logging.getLogger(__name__)


class AdaptiveTimeout:
    def __init__(
        self,
        initial: float = 10.0,
        min_t: float = 3.0,
        max_t: float = 30.0,
        history_file: Path | None = None,
    ):
        self.current_timeout = initial
        self.min_timeout = min_t
        self.max_timeout = max_t
        self.history_file = history_file or Path("data/timeout_history.json")
        # Global latencies for base timeout calculation
        self.latencies: list[float] = []
        # Per-source latencies for jitter analysis
        self.source_latencies: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._load_history()

    def _load_history(self):
        """Load previous timeout settings."""
        if self.history_file.exists():
            try:
                data = json.loads(self.history_file.read_text())
                self.current_timeout = data.get("last_timeout", self.current_timeout)
            except Exception as e:
                logger.debug(f"Failed to load timeout history: {e}")

    def get_timeout(self, source: str) -> float:
        """Get timeout for a source. Currently ignores source but ready for expansion."""
        return self.current_timeout

    async def record_attempt(self, source: str, duration: float, success: bool = True):
        """
        Record a fetch attempt.
        Failures are treated as high-latency events (using the full timeout duration)
        to encourage adaptive backoff.
        """
        # For simplicity, we treat both success and failure durations as valid data points.
        # Failures (timeouts) naturally contribute high values to the p95 calculation,
        # increasing the timeout, which is the desired adaptive behavior.
        await self.record(source, duration)

    async def record(self, source: str, latency: float):
        """
        Record a successful connection latency (async-safe with lock).

        Args:
            source: The source URL
            latency: Latency in seconds
        """
        async with self._lock:
            val = latency
            if val > 100:
                logger.debug(f"High latency recorded: {val}s (likely ms?)")

            # Update global list
            self.latencies.append(val)
            if len(self.latencies) > 100:
                self.latencies.pop(0)

            # Update per-source list with LRU eviction for DOS protection
            # Limit total unique sources to prevent unbounded memory growth
            MAX_SOURCES = 1000
            if (
                source not in self.source_latencies
                and len(self.source_latencies) >= MAX_SOURCES
            ):
                # Evict oldest source (first key in dict - Python 3.7+ maintains insertion order)
                oldest = next(iter(self.source_latencies))
                del self.source_latencies[oldest]
                safe_source = SecurityValidator.sanitize_log_message(str(oldest))
                logger.debug(
                    f"Evicted oldest source {safe_source} from latency tracking"
                )

            s_list = self.source_latencies[source]
            s_list.append(val)
            if len(s_list) > 20:  # Keep window small for source jitter
                s_list.pop(0)

            self.update()

    async def get_jitter(self, source: str) -> float:
        """
        Calculate the standard deviation (jitter) of latency for a source (async-safe).
        Returns 0.0 if insufficient data.
        """
        async with self._lock:
            data = self.source_latencies.get(source, [])
            if len(data) < 2:
                return 0.0
            try:
                return statistics.stdev(data)
            except statistics.StatisticsError:
                return 0.0

    def update(self):
        """Recalculate optimal timeout."""
        if not self.latencies:
            return

        try:
            # Require a statistically meaningful sample before adapting.
            if len(self.latencies) < 20:
                return

            ordered = sorted(self.latencies)
            p95_index = int((len(ordered) - 1) * 0.95)
            p95 = ordered[max(0, min(len(ordered) - 1, p95_index))]

            # Safety margin: 2x the p95 latency, but bounded
            new_target = p95 * 2.0

            # Smoothing: Moving average
            # Using 0.2 (20%) as smoothing factor for stability.
            alpha = 0.2
            self.current_timeout = (alpha * new_target) + (
                (1 - alpha) * self.current_timeout
            )

            # Clamp
            self.current_timeout = max(
                self.min_timeout, min(self.max_timeout, self.current_timeout)
            )

            logger.debug(
                f"Adaptive Timeout adjusted to: {self.current_timeout:.2f}s (p95: {p95:.2f}s)"
            )

        except statistics.StatisticsError as e:
            logger.debug(f"Not enough data for timeout stats: {e}")

    def save(self):
        """Persist state atomically (temp file + atomic rename + fsync).

        Using a plain ``write_text`` here risked leaving a truncated/corrupt
        JSON file if the process crashed or two runs raced, which would then
        break the loader on startup.
        """
        try:
            AtomicFileWriter.write_text(
                self.history_file,
                json.dumps({"last_timeout": self.current_timeout}),
            )
        except Exception as e:
            logger.warning(f"Failed to save timeout history: {e}")
