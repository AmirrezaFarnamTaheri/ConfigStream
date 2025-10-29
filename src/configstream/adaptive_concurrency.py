from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional
from pathlib import Path

from .metrics_emitter import MetricsEmitter, HostMetrics

class HostWindow:
    """Tracks performance metrics for a single host over a rolling window."""
    __slots__ = ("latencies", "successes", "errors", "limit")

    def __init__(self, initial_limit: int = 2):
        self.latencies: Deque[float] = deque(maxlen=100)  # Store last 100 latencies
        self.successes: int = 0
        self.errors: int = 0
        self.limit: int = initial_limit

    def record(self, latency: float, success: bool) -> None:
        """Record a single request's outcome."""
        self.latencies.append(latency)
        if success:
            self.successes += 1
        else:
            self.errors += 1

    def adjust(self, min_limit: int, max_limit: int) -> Optional[Dict[str, float]]:
        """Adjust the concurrency limit and return the metrics."""
        if not self.latencies:
            return None

        # Sort latencies to find percentiles
        lat_sorted = sorted(self.latencies)
        p50 = lat_sorted[len(lat_sorted) // 2]
        p95_index = max(0, int(len(lat_sorted) * 0.95) - 1)
        p95 = lat_sorted[p95_index]

        total_requests = self.successes + self.errors
        error_rate = self.errors / total_requests if total_requests > 0 else 0.0

        is_bad = error_rate > 0.02
        is_slow = p95 > 1.5 or p50 > 0.4

        if is_bad or is_slow:
            self.limit = max(min_limit, self.limit // 2)
        else:
            self.limit = min(max_limit, self.limit + 1)

        metrics = {
            "p50_latency": p50,
            "p95_latency": p95,
            "error_rate": error_rate,
            "concurrency_limit": self.limit,
        }

        # Reset stats for the next window
        self.latencies.clear()
        self.successes = 0
        self.errors = 0

        return metrics

class AIMDController:
    """Manages adaptive concurrency for multiple hosts."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        initial_limit: int = 2,
        min_limit: int = 1,
        max_limit: int = 32,
        adjust_interval: float = 2.0,
        metrics_emitter: Optional[MetricsEmitter] = None,
    ):
        self._host_windows: Dict[str, HostWindow] = defaultdict(lambda: HostWindow(initial_limit))
        self._metrics_emitter = metrics_emitter
        self._host_semaphores: Dict[str, asyncio.Semaphore] = defaultdict(lambda: asyncio.Semaphore(initial_limit))
        self._loop = loop
        self._initial_limit = initial_limit
        self._min_limit = min_limit
        self._max_limit = max_limit
        self._adjust_interval = adjust_interval
        self._tuner_task: asyncio.Task | None = None

    def start_tuner(self) -> None:
        """Starts the background task that periodically adjusts concurrency limits."""
        if self._tuner_task is None:
            self._tuner_task = self._loop.create_task(self._tuner())

    async def stop_tuner(self) -> None:
        """Stops the background tuner task."""
        if self._tuner_task:
            self._tuner_task.cancel()
            try:
                await self._tuner_task
            except asyncio.CancelledError:
                pass
            self._tuner_task = None

    def get_semaphore(self, host: str) -> asyncio.Semaphore:
        """Get the semaphore for a given host."""
        return self._host_semaphores[host]

    def record(self, host: str, latency: float, success: bool) -> None:
        """Record the outcome of a request for a specific host."""
        self._host_windows[host].record(latency, success)

    async def _tuner(self) -> None:
        """Periodically adjusts semaphore limits for all hosts."""
        while True:
            await asyncio.sleep(self._adjust_interval)
            for host, window in self._host_windows.items():
                old_limit = window.limit
                metrics = window.adjust(self._min_limit, self._max_limit)

                if self._metrics_emitter and metrics:
                    self._metrics_emitter.record(HostMetrics(host=host, **metrics))

                if old_limit != window.limit:
                    # To prevent deadlocks, we must drain the old semaphore
                    # before replacing it.
                    old_semaphore = self._host_semaphores[host]
                    new_semaphore = asyncio.Semaphore(window.limit)

                    # Release all waiters on the old semaphore so they can
                    # re-acquire on the new one.
                    for _ in range(old_semaphore._value):
                        try:
                            old_semaphore.release()
                        except ValueError:
                            pass # Already at max value

                    self._host_semaphores[host] = new_semaphore
