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
    def __init__(self, initial: float = 10.0, min_t: float = 3.0, max_t: float = 30.0):
        self.current_timeout = initial
        self.min_timeout = min_t
        self.max_timeout = max_t
        self.history_file = Path("data/timeout_history.json")
        self.latencies: list[float] = []
        self._load_history()

    def _load_history(self):
        """Load previous timeout settings."""
        if self.history_file.exists():
            try:
                data = json.loads(self.history_file.read_text())
                self.current_timeout = data.get("last_timeout", self.current_timeout)
            except Exception:
                pass

    def get_timeout(self, source: str) -> float:
        """Get timeout for a source. Currently ignores source but ready for expansion."""
        return self.current_timeout

    def record(self, source: str, latency_ms: float):
        """Record a successful connection latency."""
        # Handle latency in seconds or ms
        val = latency_ms
        if val > 100:  # Assume ms
            val = val / 1000.0

        self.latencies.append(val)
        # Keep window small
        if len(self.latencies) > 100:
            self.latencies.pop(0)
        self.update()

    def update(self):
        """Recalculate optimal timeout."""
        if not self.latencies:
            return

        # Calculate p95 latency
        try:
            p95 = statistics.quantiles(self.latencies, n=20)[18]  # 95th percentile

            # Safety margin: 2x the p95 latency, but bounded
            new_target = p95 * 2.0

            # Smoothing: Moving average
            self.current_timeout = (self.current_timeout * 0.8) + (new_target * 0.2)

            # Clamp
            self.current_timeout = max(
                self.min_timeout, min(self.max_timeout, self.current_timeout)
            )

            logger.debug(
                f"Adaptive Timeout adjusted to: {self.current_timeout:.2f}s (p95: {p95:.2f}s)"
            )

        except statistics.StatisticsError:
            pass

    def save(self):
        """Persist state."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self.history_file.write_text(
                json.dumps({"last_timeout": self.current_timeout})
            )
        except Exception as e:
            logger.warning(f"Failed to save timeout history: {e}")
