# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Core utilities for ConfigStream.
Includes atomic file operations and advanced concurrency primitives.
"""

import asyncio
import logging
import os
import json
import tempfile
import sys
import time
from pathlib import Path
from typing import Union, Any
from contextlib import asynccontextmanager
from .log_sanitizer import sanitize_log_message

logger = logging.getLogger(__name__)


# Cross-platform file locking helpers (best-effort; avoid new dependencies).
if sys.platform != "win32":
    try:
        import fcntl  # type: ignore
    except Exception:  # pragma: no cover - platform-specific
        logging.getLogger(__name__).debug("Suppressed broad exception")
        fcntl = None  # type: ignore
    msvcrt = None  # type: ignore
else:
    fcntl = None  # type: ignore
    try:
        import msvcrt  # type: ignore
    except Exception:  # pragma: no cover - platform-specific
        logging.getLogger(__name__).debug("Suppressed broad exception")
        msvcrt = None  # type: ignore


class _FileLock:
    """Best-effort cross-platform file lock using a lock file."""

    def __init__(self, lock_path: Path, retries: int = 10, delay: float = 0.05):
        self.lock_path = lock_path
        self.retries = max(1, int(retries))
        self.delay = max(0.0, float(delay))
        self._fh = None

    def __enter__(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.lock_path, "a+", encoding="utf-8")
        acquired = False
        try:
            # Always lock the same byte, even when the lock file is nonempty.
            self._fh.seek(0)
            if fcntl:
                fcntl.flock(self._fh, fcntl.LOCK_EX)
            elif msvcrt:
                # Non-blocking attempts first, then fallback to blocking.
                for _ in range(self.retries):
                    try:
                        msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        time.sleep(self.delay)
                else:
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_LOCK, 1)
            acquired = True
        finally:
            if not acquired:
                # __exit__ is not called when __enter__ fails.
                self._fh.close()
                self._fh = None
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._fh:
            try:
                if fcntl:
                    fcntl.flock(self._fh, fcntl.LOCK_UN)
                elif msvcrt:
                    try:
                        self._fh.seek(0)
                        msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
            finally:
                try:
                    self._fh.close()
                except OSError:
                    pass


def save_json_file(data: Any, path: str) -> None:
    """Helper to save data as JSON atomically."""
    AtomicFileWriter.write_text(path, json.dumps(data, indent=2))


def _fsync_parent_dir(path: Path) -> None:
    """fsync the directory holding *path* so a rename survives a crash.

    os.replace makes the swap atomic, but the directory entry it creates is
    not guaranteed durable until the directory itself is fsynced. Best-effort:
    platforms that cannot open a directory for fsync (notably Windows) are
    silently skipped, since durability there is provided differently.
    """
    if sys.platform == "win32":
        return
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError as exc:  # pragma: no cover - filesystem-specific
        logger.debug("Directory fsync skipped for %s: %s", path.parent, exc)
    finally:
        os.close(dir_fd)


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

        lock_path = path.parent / f".{path.name}.lock"
        with _FileLock(lock_path):
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

                # Atomic rename with retries (Windows can fail if file is in use)
                for attempt in range(10):
                    try:
                        os.replace(temp_path, path)
                        break
                    except OSError as e:
                        if getattr(e, "winerror", None) in (5, 32) or getattr(
                            e, "errno", None
                        ) in (13, 32):
                            time.sleep(0.05 * (attempt + 1))
                            continue
                        raise
                else:
                    raise OSError("Atomic replace failed after retries")
                # Make the rename itself durable, not just the file contents.
                _fsync_parent_dir(path)
            except Exception as e:
                logger.error(
                    "Failed to write atomically: %s",
                    sanitize_log_message(f"{path}: {e}"),
                )
                # Cleanup temp file if it exists
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except OSError as e_cleanup:
                        logger.debug(
                            "Failed to cleanup temp file: %s",
                            sanitize_log_message(f"{temp_path}: {e_cleanup}"),
                        )
                raise

    @staticmethod
    def write_bytes(path: Union[str, Path], content: bytes) -> None:
        """Write bytes to file atomically."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        lock_path = path.parent / f".{path.name}.lock"
        with _FileLock(lock_path):
            temp_path = None
            try:
                fd, temp_path = tempfile.mkstemp(
                    dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
                )
                with os.fdopen(fd, "wb") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())

                for attempt in range(10):
                    try:
                        os.replace(temp_path, path)
                        break
                    except OSError as e:
                        if getattr(e, "winerror", None) in (5, 32) or getattr(
                            e, "errno", None
                        ) in (13, 32):
                            time.sleep(0.05 * (attempt + 1))
                            continue
                        raise
                else:
                    raise OSError("Atomic replace failed after retries")
                # Make the rename itself durable, not just the file contents.
                _fsync_parent_dir(path)
            except Exception as e:
                logger.error(
                    "Failed to write atomically: %s",
                    sanitize_log_message(f"{path}: {e}"),
                )
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except OSError as e_cleanup:
                        logger.debug(
                            "Failed to cleanup temp file: %s",
                            sanitize_log_message(f"{temp_path}: {e_cleanup}"),
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

    @property
    def active_count(self) -> int:
        """Expose active permit count for monitoring/diagnostics."""
        return self._active

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
                # Guard against negative active count from double-release
                self._active = max(0, self._active - 1)
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
            # Guard against negative active count
            self._active = max(0, self._active - 1)
            self._cond.notify()

    async def set_limit(self, new_limit: int):
        """Dynamically set the concurrency limit."""
        async with self._cond:
            self._limit = new_limit
            # If we increased the limit, wake up waiters to check if they can run
            if self._active < self._limit:
                self._cond.notify_all()

    async def drain(self, timeout: float = 30.0) -> bool:
        """Wait for all active permits to be released.

        Useful during graceful shutdown to ensure no tasks are orphaned.
        Returns True if drained within timeout, False otherwise.
        """
        deadline = time.monotonic() + timeout
        async with self._cond:
            while self._active > 0:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    logger.warning(
                        f"BoundedConcurrencyManager drain timed out with {self._active} active permits"
                    )
                    return False
                try:
                    await asyncio.wait_for(self._cond.wait(), timeout=remaining)
                except asyncio.TimeoutError:
                    return False
        return True
