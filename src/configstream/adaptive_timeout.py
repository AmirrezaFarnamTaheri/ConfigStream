"""
Adaptive Timeout Strategy
Dynamically adjusts request timeouts based on historical performance per source.
"""

from __future__ import annotations

import statistics
import sqlite3
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AdaptiveTimeout:
    """
    Track historical fetch performance and calculate adaptive timeouts.

    Timeout calculation:
    - New sources: Use default timeout (30s)
    - Known sources: historical_avg * 2, capped between 10-60s
    - Keeps last 50 data points per source for trend analysis
    """

    def __init__(self, db_path: Path | str | None = None, default_timeout: int = 30):
        """
        Initialize adaptive timeout tracker.

        Args:
            db_path: Path to SQLite database for persistence
            default_timeout: Default timeout for unknown sources
        """
        self.default_timeout = default_timeout
        self.db_path = Path(db_path) if db_path else Path("data/adaptive_timeout.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory cache for fast lookups
        self._cache: Dict[str, List[float]] = {}

        # Initialize database
        self._init_db()
        self._load_cache()

    def _init_db(self) -> None:
        """Create database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS timeout_history (
                        source TEXT NOT NULL,
                        duration REAL NOT NULL,
                        timestamp INTEGER NOT NULL,
                        PRIMARY KEY (source, timestamp)
                    )
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_source_timestamp
                    ON timeout_history(source, timestamp DESC)
                """
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(
                "Failed to initialize adaptive timeout database at %s: %s",
                self.db_path,
                e,
            )

    def _load_cache(self) -> None:
        """Load recent history into memory cache."""
        cutoff = datetime.now() - timedelta(days=7)
        cutoff_ts = int(cutoff.timestamp())

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT source, duration
                FROM timeout_history
                WHERE timestamp > ?
                ORDER BY source, timestamp DESC
            """,
                (cutoff_ts,),
            )

            for source, duration in cursor:
                if source not in self._cache:
                    self._cache[source] = []
                self._cache[source].append(duration)
                # Enforce in-memory cap to avoid unbounded growth
                if len(self._cache[source]) > 50:
                    self._cache[source] = self._cache[source][:50]

        logger.info("Loaded timeout history for %d sources", len(self._cache))

    def get_timeout(self, source_url: str) -> int:
        """
        Calculate adaptive timeout for a source.

        Args:
            source_url: The source URL to fetch

        Returns:
            Timeout in seconds (10-60 range)
        """
        if source_url not in self._cache or not self._cache[source_url]:
            return self.default_timeout

        # Use last 10 fetches for recent trend
        recent = self._cache[source_url][:10]

        try:
            avg_duration = statistics.mean(recent)

            # Add 100% buffer (2x average) for safety
            calculated_timeout = int(avg_duration * 2)

            # Clamp to reasonable range (10-60 seconds)
            adaptive_timeout = max(10, min(calculated_timeout, 60))

            logger.debug(
                "Adaptive timeout for %s: %ds (avg: %.1fs, samples: %d)",
                source_url[:50],
                adaptive_timeout,
                avg_duration,
                len(recent),
            )

            return adaptive_timeout

        except statistics.StatisticsError:
            logger.warning("Failed to calculate stats for %s, using default", source_url)
            return self.default_timeout

    def record(self, source_url: str, duration: float) -> None:
        """
        Record a successful fetch duration.

        Args:
            source_url: The source URL
            duration: Fetch duration in seconds
        """
        # Update in-memory cache
        if source_url not in self._cache:
            self._cache[source_url] = []

        self._cache[source_url].insert(0, duration)

        # Keep only last 50 entries
        self._cache[source_url] = self._cache[source_url][:50]

        # Persist to database
        timestamp = int(datetime.now().timestamp())

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO timeout_history (source, duration, timestamp)
                    VALUES (?, ?, ?)
                """,
                    (source_url, duration, timestamp),
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.warning("Failed to persist timeout history: %s", e)

    def cleanup_old_entries(self, days: int = 30) -> int:
        """
        Remove entries older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of entries deleted
        """
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_ts = int(cutoff.timestamp())

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM timeout_history
                    WHERE timestamp < ?
                """,
                    (cutoff_ts,),
                )
                deleted = cursor.rowcount
                conn.commit()

            logger.info("Cleaned up %d old timeout entries", deleted)
            return deleted

        except sqlite3.Error as e:
            logger.error("Failed to cleanup timeout history: %s", e)
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about tracked sources.

        Returns:
            Dictionary with statistics
        """
        total_sources = len(self._cache)
        total_samples = sum(len(history) for history in self._cache.values())

        if total_samples == 0:
            return {
                "total_sources": 0,
                "total_samples": 0,
                "avg_timeout": self.default_timeout,
                "min_timeout": self.default_timeout,
                "max_timeout": self.default_timeout,
            }

        all_timeouts = [self.get_timeout(source) for source in self._cache.keys()]

        return {
            "total_sources": total_sources,
            "total_samples": total_samples,
            "avg_timeout": statistics.mean(all_timeouts) if all_timeouts else self.default_timeout,
            "min_timeout": min(all_timeouts) if all_timeouts else self.default_timeout,
            "max_timeout": max(all_timeouts) if all_timeouts else self.default_timeout,
        }


# Global instance for convenience
_global_timeout_tracker: Optional[AdaptiveTimeout] = None


def get_timeout_tracker(db_path: Path | str | None = None) -> AdaptiveTimeout:
    """Get or create the global timeout tracker instance."""
    global _global_timeout_tracker
    if _global_timeout_tracker is None:
        _global_timeout_tracker = AdaptiveTimeout(db_path)
    return _global_timeout_tracker
