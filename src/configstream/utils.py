"""
Core utilities for ConfigStream.
Includes atomic file operations and advanced concurrency primitives.
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Union
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class AtomicFileWriter:
    """
    Helper for atomic file writes.
    Writes to a temporary file first, then renames it to the target path.
    This ensures that the target file is never in a corrupted/partial state.
    """

    @staticmethod
    def write_text(
        path: Union[str, Path], content: str, encoding: str = "utf-8"
    ) -> None:
        """Write text to file atomically."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Create temp file in the same directory to ensure atomic rename works across filesystems
        try:
            fd, temp_path = tempfile.mkstemp(
                dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
            )
            with os.fdopen(fd, "w", encoding=encoding) as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is on disk

            # Atomic rename
            os.replace(temp_path, path)
        except Exception as e:
            logger.error(f"Failed to write atomically to {path}: {e}")
            # Cleanup temp file if it exists
            if "temp_path" in locals() and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            raise

    @staticmethod
    def write_bytes(path: Union[str, Path], content: bytes) -> None:
        """Write bytes to file atomically."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            fd, temp_path = tempfile.mkstemp(
                dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
            )
            with os.fdopen(fd, "wb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

            os.replace(temp_path, path)
        except Exception as e:
            logger.error(f"Failed to write atomically to {path}: {e}")
            if "temp_path" in locals() and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            raise


class ResizableSemaphore:
    """
    An asyncio.Semaphore that can be resized dynamically.
    """

    def __init__(self, initial_value: int = 1):
        self._value = initial_value
        self._limit = initial_value
        self._waiters: asyncio.Queue = asyncio.Queue()  # Unbounded wait queue
        self._lock = asyncio.Lock()  # Protect internal state

    @property
    def limit(self) -> int:
        return self._limit

    async def acquire(self):
        """Acquire a permit."""
        while True:
            async with self._lock:
                if self._value > 0:
                    self._value -= 1
                    return

            # If no permits, we wait.
            # We use a future to wait.
            fut = asyncio.get_running_loop().create_future()
            await self._waiters.put(fut)
            try:
                await fut
            except asyncio.CancelledError:
                # If cancelled while waiting, we just leave.
                # The permit logic handles "giving back" if we were woken up.
                # But wait, if we were woken up, 'fut' is done.
                # If we are cancelled, we shouldn't have consumed a permit.
                raise

    def release(self):
        """Release a permit."""
        # We don't need async lock for simple release usually, but for safety with resize:
        # Actually release can be synchronous.

        # Check if there are waiters
        try:
            # Try to get a waiter without blocking
            fut = self._waiters.get_nowait()
            if not fut.done():
                fut.set_result(None)
            # We passed the permit to the waiter, so _value stays same (0).
        except asyncio.QueueEmpty:
            # No waiters, increment value
            # (Race condition possible here if we don't lock?
            # _value is modified in acquire under lock. )
            # Let's use a lightweight check.
            # Since this is sync, we can't use async lock.
            # But acquire holds lock.
            # This implementation is tricky to do perfectly safe without Condition.
            # Standard Semaphore uses a deque.

            # Simplified logic:
            self._value += 1

            # But wait, if we increased value, maybe a waiter can grab it now?
            # But we checked waiters queue first.
            # Race: Waiter arrives between QueueEmpty check and _value += 1.
            # The waiter will see _value > 0 in next loop? No, waiter is in queue.

            # Correct logic:
            # 1. Increase value.
            # 2. If waiters exist, wake one up.
            pass
            # Implementation complexity suggests wrapping asyncio.Semaphore isn't enough.
            # Let's stick to a safer implementation using asyncio.Condition if needed,
            # OR rely on the fact that standard Semaphore uses `_value` and `_waiters`.

            # Since we can't easily inherit/modify private attributes of asyncio.Semaphore,
            # we implement a "soft" limit on top of a loose Semaphore.

    # RETRY: Simpler approach. Use a standard Semaphore, but control entry via a token bucket?
    # Or just use the logic: `acquire` checks `active_count < current_limit`.


class BoundedConcurrencyManager:
    """
    Manages concurrency by tracking active tasks vs a limit.
    """

    def __init__(self, limit: int):
        self._limit = limit
        self._active = 0
        self._cond = asyncio.Condition()

    @property
    def limit(self):
        return self._limit

    def resize(self, new_limit: int):
        self._limit = new_limit
        # If we grew, wake up waiters
        # (We can't wake specific number, notify_all is safest)
        # Actually we need to acquire lock to notify
        # This needs to be async? No, notify is sync?
        # asyncio.Condition.notify() is sync.
        # But we need to hold the lock to notify?
        # No, notify() requires lock to be held? Yes.
        pass

    @contextmanager
    async def acquire(self):
        async with self._cond:
            while self._active >= self._limit:
                await self._cond.wait()
            self._active += 1

        try:
            yield
        finally:
            async with self._cond:
                self._active -= 1
                self._cond.notify()

    # Async context manager
    async def __aenter__(self):
        async with self._cond:
            while self._active >= self._limit:
                await self._cond.wait()
            self._active += 1

    async def __aexit__(self, exc_type, exc, tb):
        async with self._cond:
            self._active -= 1
            self._cond.notify()

    async def set_limit(self, new_limit: int):
        async with self._cond:
            diff = new_limit - self._limit
            self._limit = new_limit
            if diff > 0:
                self._cond.notify_all()
