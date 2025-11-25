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
                logger.debug(f"Evicted oldest source {oldest} from latency tracking")

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

        # Calculate p95 latency
        try:
            if len(self.latencies) < 2:
                return

            # Use percentile for more robust calculation
            # statistics.quantiles(data, n=100) returns 99 values (percentiles 1-99)
            # For 95th percentile, we want index 94
            p95 = statistics.quantiles(self.latencies, n=100)[94]  # 95th percentile

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
        """Persist state."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self.history_file.write_text(
                json.dumps({"last_timeout": self.current_timeout})
            )
        except Exception as e:
            logger.warning(f"Failed to save timeout history: {e}")
