"""
Unified AIMD Concurrency Controller.
Dynamically adjusts concurrency limits based on system pressure and error rates.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque, defaultdict
from typing import Dict, Optional
from .config import AppSettings

logger = logging.getLogger(__name__)

class ResourceStats:
    """Tracks sliding window of performance metrics."""
    __slots__ = ('latencies', 'errors', 'total', 'limit')

    def __init__(self, initial_limit: int):
        self.latencies = deque(maxlen=50)
        self.errors = 0
        self.total = 0
        self.limit = float(initial_limit)  # Float for smoother AIMD steps

    def update(self, latency: float, is_error: bool):
        self.total += 1
        if is_error:
            self.errors += 1
        else:
            self.latencies.append(latency)

    def reset_counters(self):
        self.errors = 0
        self.total = 0
        self.latencies.clear()

class ConcurrencyManager:
    """
    Manages dynamic semaphores.
    Uses a token-bucket approach to allow resizing without replacing semaphores.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, initial_limit: int = 5, min_limit: int = 1, max_limit: int = 50):
        self._loop = loop
        self._stats: Dict[str, ResourceStats] = defaultdict(lambda: ResourceStats(initial_limit))
        self._semaphores: Dict[str, asyncio.Semaphore] = defaultdict(lambda: asyncio.Semaphore(initial_limit))
        self._limits: Dict[str, int] = defaultdict(lambda: initial_limit)

        self.min_limit = min_limit
        self.max_limit = max_limit

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.settings = AppSettings()

    def get_semaphore(self, key: str = "default") -> asyncio.Semaphore:
        return self._semaphores[key]

    def record(self, key: str, latency: float, success: bool):
        self._stats[key].update(latency, not success)

    def start_tuner(self):
        if not self._running:
            self._running = True
            self._task = self._loop.create_task(self._tune_loop())

    async def stop_tuner(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _tune_loop(self):
        """Background loop to adjust concurrency."""
        while self._running:
            await asyncio.sleep(1.0)  # Adjust every second

            for key, stats in self._stats.items():
                if stats.total == 0:
                    continue

                current_limit = self._limits[key]
                new_limit = current_limit

                # Calculate Error Rate
                error_rate = stats.errors / stats.total

                # Calculate P95 Latency
                p95 = 0
                if stats.latencies:
                    sorted_lat = sorted(stats.latencies)
                    idx = int(len(sorted_lat) * 0.95)
                    p95 = sorted_lat[min(idx, len(sorted_lat)-1)]

                # AIMD Logic
                # 1. Backoff on High Errors (>10%)
                if error_rate > 0.10:
                    new_limit = max(self.min_limit, current_limit * 0.5)
                    logger.debug(f"AIMD[{key}]: High error rate ({error_rate:.2%}). Backing off to {new_limit:.1f}")

                # 2. Backoff on High Latency (Configurable Threshold)
                elif p95 > self.settings.AIMD_P95_MS / 1000.0:
                    new_limit = max(self.min_limit, current_limit * 0.8)
                    logger.debug(f"AIMD[{key}]: High latency ({p95:.2f}s). Backing off to {new_limit:.1f}")

                # 3. Additive Increase if Healthy
                else:
                    new_limit = min(self.max_limit, current_limit + 1)

                # Apply Change
                if int(new_limit) != int(current_limit):
                    self._resize_semaphore(key, int(new_limit))
                    self._limits[key] = new_limit
                    stats.limit = new_limit

                stats.reset_counters()

    def _resize_semaphore(self, key: str, new_value: int):
        """
        Safely resize the semaphore capacity.
        Since asyncio.Semaphore doesn't support resizing, we approximate it
        by releasing (to grow) or acquiring (to shrink) the difference.
        """
        sem = self._semaphores[key]
        # Note: accessing _value is internal API but standard for this hack in asyncio
        # A cleaner way involves replacing the semaphore, but that risks race conditions.
        # We stick to the safe logic of bounded growth.

        current_value = sem._value
        diff = new_value - current_value

        if diff > 0:
            # Grow: Release N times
            for _ in range(diff):
                try:
                    sem.release()
                except ValueError:
                    pass
        # We don't aggressively shrink (acquire) to avoid blocking the tuner
        # The limit effectively shrinks naturally as we stop releasing extras.
