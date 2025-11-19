"""
Adaptive Timeout Strategy
Dynamically adjusts request timeouts based on historical performance.
Optimized for async execution with non-blocking writes.
"""

from __future__ import annotations

import statistics
import sqlite3
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)

class AdaptiveTimeout:
    """
    Async-optimized timeout tracker.
    Uses an in-memory write buffer to prevent blocking the event loop.
    """

    def __init__(self, db_path: Path | str | None = None, default_timeout: int = 30):
        self.default_timeout = default_timeout
        self.db_path = Path(db_path) if db_path else Path("data/adaptive_timeout.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Fast in-memory lookups
        self._cache: Dict[str, deque] = {}
        self._dirty_queue: deque = deque()
        self._lock = asyncio.Lock()

        # Initialize DB synchronously at startup (safe)
        self._init_db()
        self._load_cache()

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS timeout_history (
                        source TEXT NOT NULL,
                        duration REAL NOT NULL,
                        timestamp INTEGER NOT NULL
                    )
                """)
                # Index for fast loading
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_source_ts
                    ON timeout_history(source, timestamp DESC)
                """)
                conn.commit()
        except Exception as e:
            logger.error("Failed to init timeout DB: %s", e)

    def _load_cache(self) -> None:
        """Warm up the cache from disk."""
        cutoff = int((datetime.now() - timedelta(days=7)).timestamp())
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT source, duration FROM timeout_history
                    WHERE timestamp > ?
                """, (cutoff,))

                for source, duration in cursor:
                    if source not in self._cache:
                        self._cache[source] = deque(maxlen=20)
                    self._cache[source].append(duration)
        except Exception as e:
            logger.warning("Failed to load timeout cache: %s", e)

    def get_timeout(self, source_url: str) -> int:
        """
        Get timeout for a source.
        This is CPU-bound only (fast), no IO.
        """
        history = self._cache.get(source_url)
        if not history:
            return self.default_timeout

        try:
            avg_duration = statistics.mean(history)
            # Safety margin: 2x average or +5s, whichever is safer
            calculated = int(max(avg_duration * 2, avg_duration + 5))
            # Clamp: Never below 5s, never above 60s (unless default is higher)
            return max(5, min(calculated, 60))
        except statistics.StatisticsError:
            return self.default_timeout

    def record(self, source_url: str, duration: float) -> None:
        """
        Record a metric.
        Updates memory immediately, queues DB write for later.
        """
        if duration <= 0 or duration > 300:
            return

        if source_url not in self._cache:
            self._cache[source_url] = deque(maxlen=20)

        self._cache[source_url].append(duration)

        # Add to write buffer
        ts = int(datetime.now().timestamp())
        self._dirty_queue.append((source_url, duration, ts))

    def save(self) -> None:
        """
        Flush memory buffer to disk.
        Call this at the end of the pipeline or periodically.
        """
        if not self._dirty_queue:
            return

        batch = []
        while self._dirty_queue:
            batch.append(self._dirty_queue.popleft())

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executemany("""
                    INSERT INTO timeout_history (source, duration, timestamp)
                    VALUES (?, ?, ?)
                """, batch)
                conn.commit()
                logger.info("Flushed %d timeout metrics to disk", len(batch))
        except Exception as e:
            logger.error("Failed to flush timeout metrics: %s", e)
