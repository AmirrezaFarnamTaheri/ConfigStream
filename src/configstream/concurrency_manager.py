"""
Concurrency Manager
Dynamically adjusts concurrency limits based on system load and error rates (AIMD).
"""

import asyncio
import logging
from collections import deque
from typing import Deque, Optional
from .utils import BoundedConcurrencyManager as ResizableSemaphore

logger = logging.getLogger(__name__)


class ConcurrencyManager:
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        initial_limit: int = 50,
        min_limit: int = 10,
        max_limit: int = 500,
        error_threshold: float = 0.1,
        backoff_factor: float = 0.7,
    ):
        self.loop = loop
        self.current_limit = initial_limit
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.error_threshold = error_threshold
        self.backoff_factor = backoff_factor

        self.semaphore = ResizableSemaphore(initial_limit)
        self.latencies: Deque[float] = deque(maxlen=100)
        self.errors: Deque[bool] = deque(maxlen=100)
        self._stats_lock = asyncio.Lock()  # Protect deque access

        self.tuning_task: Optional[asyncio.Task] = None
        self._running = False
        # [FIX] Protect start/stop logic with a lock to prevent race conditions
        self._lifecycle_lock = asyncio.Lock()

    def get_semaphore(self) -> ResizableSemaphore:
        return self.semaphore

    async def record(self, host: str, latency: float, success: bool):
        """Record request outcome."""
        async with self._stats_lock:
            self.latencies.append(latency)
            self.errors.append(not success)

    async def _tuner_loop(self):
        """Periodically adjust concurrency limit."""
        while self._running:
            try:
                await asyncio.sleep(1.0)
                await self._adjust()
            except (asyncio.CancelledError, KeyboardInterrupt):
                # Tuner loop cancelled
                break
            except Exception as e:
                logger.error(f"Error in tuner loop: {e}")

    async def _adjust(self):
        async with self._stats_lock:
            if not self.errors:
                return

            # Count True in errors (which means failure)
            error_count = sum(1 for e in self.errors if e)
            error_rate = error_count / len(self.errors)

        # Perform adjustment outside lock (doesn't need lock)

        if error_rate > self.error_threshold:
            # High errors -> Multiplicative Decrease
            new_limit = max(
                self.min_limit, int(self.current_limit * self.backoff_factor)
            )
            if new_limit != self.current_limit:
                logger.debug(
                    f"High error rate ({error_rate:.2f}). Decreasing concurrency to {new_limit}"
                )
                # This is running in a loop task, so we can await
                await self._resize_semaphore(new_limit)
        elif error_rate < 0.01:
            # Low errors -> Additive Increase
            new_limit = min(self.max_limit, self.current_limit + 5)
            if new_limit != self.current_limit:
                logger.debug(f"Low error rate. Increasing concurrency to {new_limit}")
                await self._resize_semaphore(new_limit)

    async def _resize_semaphore(self, new_limit: int):
        # Uses the BoundedConcurrencyManager's resize mechanism
        # Note: set_limit is async because it needs to acquire lock to notify
        self.current_limit = new_limit
        await self.semaphore.set_limit(new_limit)

    # [FIX] Made async to use await with lifecycle_lock
    async def start_tuner(self):
        async with self._lifecycle_lock:
            if not self._running:
                # Check if loop is still running before creating task
                if self.loop.is_closed():
                    return
                self._running = True
                self.tuning_task = self.loop.create_task(self._tuner_loop())

    async def stop_tuner(self):
        async with self._lifecycle_lock:
            if not self._running:
                return
            self._running = False

            if self.tuning_task:
                self.tuning_task.cancel()
                try:
                    await self.tuning_task
                except (asyncio.CancelledError, KeyboardInterrupt):
                    pass
                except Exception as e:
                    logger.warning(f"Error while stopping tuner: {e}")
                finally:
                    self.tuning_task = None
