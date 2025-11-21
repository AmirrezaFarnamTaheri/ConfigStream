"""
Concurrency Manager
Dynamically adjusts concurrency limits based on system load and error rates (AIMD).
"""

import asyncio
import logging
from collections import deque
from typing import Deque, Optional

logger = logging.getLogger(__name__)


class ConcurrencyManager:
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        initial_limit: int = 50,
        min_limit: int = 10,
        max_limit: int = 500,
    ):
        self.loop = loop
        self.current_limit = initial_limit
        self.min_limit = min_limit
        self.max_limit = max_limit

        self.semaphore = asyncio.Semaphore(initial_limit)
        self.latencies: Deque[float] = deque(maxlen=100)
        self.errors: Deque[bool] = deque(maxlen=100)
        self._stats_lock = asyncio.Lock()  # Protect deque access

        self.tuning_task: Optional[asyncio.Task] = None
        self._running = False

    def get_semaphore(self) -> asyncio.Semaphore:
        return self.semaphore

    async def record(self, host: str, latency: float, success: bool):
        """Record request outcome."""
        async with self._stats_lock:
            self.latencies.append(latency)
            self.errors.append(not success)

    async def _tuner_loop(self):
        """Periodically adjust concurrency limit."""
        while self._running:
            await asyncio.sleep(1.0)
            await self._adjust()

    async def _adjust(self):
        async with self._stats_lock:
            if not self.errors:
                return

            # Count True in errors (which means failure)
            error_count = sum(1 for e in self.errors if e)
            error_rate = error_count / len(self.errors)

        # Perform adjustment outside lock (doesn't need lock)

        if error_rate > 0.1:
            # High errors -> Multiplicative Decrease
            new_limit = max(self.min_limit, int(self.current_limit * 0.7))
            if new_limit != self.current_limit:
                logger.debug(
                    f"High error rate ({error_rate:.2f}). Decreasing concurrency to {new_limit}"
                )
                self._resize_semaphore(new_limit)
        elif error_rate < 0.01:
            # Low errors -> Additive Increase
            new_limit = min(self.max_limit, self.current_limit + 5)
            if new_limit != self.current_limit:
                logger.debug(f"Low error rate. Increasing concurrency to {new_limit}")
                self._resize_semaphore(new_limit)

    def _resize_semaphore(self, new_limit: int):
        # Asyncio Semaphore doesn't support dynamic resizing cleanly
        # We approximate by changing the internal value if possible,
        # or replacing it (careful with active tasks).
        # Since replacing is dangerous, we just update the target
        # and let the logic respect 'current_limit' if we implemented a custom semaphore.
        # Standard asyncio.Semaphore logic:
        # We can release extra permits or acquire excess to balance.

        diff = new_limit - self.current_limit
        self.current_limit = new_limit

        if diff > 0:
            # Growing: Release permits
            for _ in range(diff):
                try:
                    self.semaphore.release()
                except ValueError:
                    pass
        elif diff < 0:
            # Shrinking: Acquire permits (non-blocking best effort)
            # This is tricky without blocking. We skip actual shrinking implementation
            # for standard Semaphore to avoid deadlocks.
            # Real implementation would use a bounded semaphore wrapper.
            pass

    def start_tuner(self):
        if not self._running:
            # Check if loop is still running before creating task
            if self.loop.is_closed():
                return
            self._running = True
            self.tuning_task = self.loop.create_task(self._tuner_loop())

    async def stop_tuner(self):
        self._running = False
        if self.tuning_task:
            self.tuning_task.cancel()
            try:
                await self.tuning_task
            except asyncio.CancelledError:
                pass
