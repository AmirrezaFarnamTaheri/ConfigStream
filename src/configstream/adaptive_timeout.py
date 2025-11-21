"""
Adaptive Timeout Mechanism.
Dynamically adjusts socket timeouts based on network conditions.
"""

import logging
import statistics
import json
from pathlib import Path

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
        self.latencies: list[float] = []
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

    def record(self, source: str, latency: float):
        """
        Record a successful connection latency.

        Args:
            source: The source URL (currently unused for differentiation)
            latency: Latency in seconds
        """
        # We expect seconds. If someone passes > 100, it's likely ms, so we warn/convert
        # but let's strictly assume seconds as per Fetcher
        val = latency
        if val > 100:
            # Heuristic: likely ms, but technically valid seconds (slow proxy).
            # Given max_timeout defaults to 30, >100 is suspicious.
            # For now, we treat it as seconds to be "dumb but predictable".
            logger.debug(f"High latency recorded: {val}s (likely ms?)")

        self.latencies.append(val)
        # Keep window small
        if len(self.latencies) > 100:
            self.latencies.pop(0)
        # Force update on every record for testing responsiveness
        self.update()

    def update(self):
        """Recalculate optimal timeout."""
        if not self.latencies:
            return

        # Calculate p95 latency
        try:
            # If we don't have enough data for quantiles(n=20), use max or median?
            # statistics.quantiles requires at least n-1 data points? No, it requires at least 2 points.
            if len(self.latencies) < 2:
                return

            p95 = statistics.quantiles(self.latencies, n=20)[18]  # 95th percentile

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
