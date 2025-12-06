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
from contextlib import asynccontextmanager

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
        temp_path = None
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
            logger.error("Failed to write atomically to %s: %s", path, e)
            # Cleanup temp file if it exists
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError as e_cleanup:
                    logger.debug(
                        "Failed to cleanup temp file %s: %s", temp_path, e_cleanup
                    )
            raise

    @staticmethod
    def write_bytes(path: Union[str, Path], content: bytes) -> None:
        """Write bytes to file atomically."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = None
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
            logger.error("Failed to write atomically to %s: %s", path, e)
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError as e_cleanup:
                    logger.debug(
                        "Failed to cleanup temp file %s: %s", temp_path, e_cleanup
                    )
            raise


class BoundedConcurrencyManager:
    """
    Manages concurrency by tracking active tasks vs a limit.
    Supports dynamic resizing.
    """

    def __init__(self, limit: int):
        self._limit = limit
        self._active = 0
        self._cond = asyncio.Condition()

    @property
    def limit(self):
        return self._limit

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire semaphore-like lock.
        Usage: async with cm.acquire(): ...
        """
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

    # Async context manager protocol support
    async def __aenter__(self):
        async with self._cond:
            while self._active >= self._limit:
                await self._cond.wait()
            self._active += 1
        return self

    async def __aexit__(self, exc_type, exc, tb):
        async with self._cond:
            self._active -= 1
            self._cond.notify()

    async def set_limit(self, new_limit: int):
        """Dynamically set the concurrency limit."""
        async with self._cond:
            self._limit = new_limit
            # If we increased the limit, wake up waiters to check if they can run
            if self._active < self._limit:
                self._cond.notify_all()
