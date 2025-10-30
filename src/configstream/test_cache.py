"""
Test result caching system for ConfigStream.

This module provides a SQLite-based cache for proxy test results,
significantly reducing retest time by skipping recently validated proxies.
"""

import hashlib
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .models import Proxy

logger = logging.getLogger(__name__)


class TestResultCache:
    """SQLite-backed cache for proxy test results."""

    __test__ = False

    def __init__(self, db_path: str = "data/test_cache.db", ttl_seconds: int = 3600):
        """
        Initialize the test result cache.

        Args:
            db_path: Path to SQLite database file
            ttl_seconds: Time-to-live for cached results (default: 1 hour)
        """
        self.db_path = Path(db_path)
        self.ttl_seconds = ttl_seconds
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database with required schema and optimizations."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            # Enable WAL mode for better concurrency and performance
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")  # 256 MB
            conn.execute("PRAGMA cache_size=-80000")  # ~80 MB cache

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_results (
                    config_hash TEXT PRIMARY KEY,
                    config TEXT NOT NULL,
                    is_working INTEGER NOT NULL,
                    latency REAL,
                    country TEXT,
                    country_code TEXT,
                    city TEXT,
                    tested_at REAL NOT NULL,
                    test_count INTEGER DEFAULT 1,
                    success_count INTEGER DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tested_at
                ON test_results(tested_at)
                """
            )
            conn.commit()
            logger.info("Test cache initialized at %s with WAL mode", self.db_path)

    def get(self, proxy: Proxy) -> Optional[Proxy]:
        """
        Get cached test result for a proxy.

        Args:
            proxy: Proxy to look up

        Returns:
            Cached proxy with test results, or None if not cached or expired
        """
        if not proxy.config:
            return None

        config_hash = self._compute_hash(proxy.config)
        current_time = time.time()
        cutoff_time = current_time - self.ttl_seconds

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT config, is_working, latency, country, country_code,
                       city, tested_at, test_count, success_count
                FROM test_results
                WHERE config_hash = ? AND tested_at > ?
                """,
                (config_hash, cutoff_time),
            )
            row = cursor.fetchone()

            if row:
                # Update proxy with cached results
                proxy.is_working = bool(row["is_working"])
                proxy.latency = row["latency"]
                proxy.country = row["country"] or proxy.country
                proxy.country_code = row["country_code"] or proxy.country_code
                proxy.city = row["city"] or proxy.city
                proxy.tested_at = datetime.fromtimestamp(
                    row["tested_at"], tz=timezone.utc
                ).isoformat()

                logger.debug(
                    "Cache HIT for %s:%s (age: %.1fs)",
                    proxy.address,
                    proxy.port,
                    current_time - row["tested_at"],
                )
                return proxy

        logger.debug("Cache MISS for %s:%s", proxy.address, proxy.port)
        return None

    def set(self, proxy: Proxy) -> None:
        """
        Store test result in cache.

        Args:
            proxy: Proxy with test results to cache
        """
        if not proxy.config:
            return

        config_hash = self._compute_hash(proxy.config)
        current_time = time.time()

        with sqlite3.connect(self.db_path) as conn:
            # Check if entry exists
            cursor = conn.execute(
                "SELECT test_count, success_count FROM test_results WHERE config_hash = ?",
                (config_hash,),
            )
            row = cursor.fetchone()

            if row:
                # Update existing entry with incremented counters
                test_count = row[0] + 1
                success_count = row[1] + (1 if proxy.is_working else 0)
                conn.execute(
                    """
                    UPDATE test_results
                    SET is_working = ?, latency = ?, country = ?, country_code = ?,
                        city = ?, tested_at = ?, test_count = ?, success_count = ?
                    WHERE config_hash = ?
                    """,
                    (
                        int(proxy.is_working),
                        proxy.latency,
                        proxy.country,
                        proxy.country_code,
                        proxy.city,
                        current_time,
                        test_count,
                        success_count,
                        config_hash,
                    ),
                )
            else:
                # Insert new entry
                success_count = 1 if proxy.is_working else 0
                conn.execute(
                    """
                    INSERT INTO test_results
                    (config_hash, config, is_working, latency, country, country_code,
                     city, tested_at, test_count, success_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        config_hash,
                        proxy.config,
                        int(proxy.is_working),
                        proxy.latency,
                        proxy.country,
                        proxy.country_code,
                        proxy.city,
                        current_time,
                        success_count,
                    ),
                )
            conn.commit()

    def get_health_score(self, proxy: Proxy) -> float:
        """
        Get health score for a proxy based on historical test results.

        Args:
            proxy: Proxy to get health score for

        Returns:
            Health score between 0.0 and 1.0 (1.0 = always working)
        """
        if not proxy.config:
            return 0.5  # Default neutral score

        config_hash = self._compute_hash(proxy.config)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT test_count, success_count FROM test_results WHERE config_hash = ?",
                (config_hash,),
            )
            row = cursor.fetchone()

            if row and row[0] > 0:
                return float(row[1]) / float(row[0])

        return 0.5  # Default neutral score for new proxies

    @staticmethod
    def _compute_hash(config: str) -> str:
        """Return a stable hash for a configuration string."""

        digest = hashlib.sha256(config.encode("utf-8")).hexdigest()
        return digest

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        cutoff_time = current_time - self.ttl_seconds

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM test_results WHERE tested_at < ?", (cutoff_time,))
            deleted = cursor.rowcount
            conn.commit()

            if deleted > 0:
                logger.info("Cleaned up %d expired cache entries", deleted)

            return deleted

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        current_time = time.time()
        cutoff_time = current_time - self.ttl_seconds

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total_entries,
                    SUM(CASE WHEN tested_at > ? THEN 1 ELSE 0 END) as valid_entries,
                    AVG(
                        CASE WHEN tested_at > ?
                        THEN success_count * 1.0 / test_count
                        ELSE NULL END
                    ) as avg_health_score
                FROM test_results
                """,
                (cutoff_time, cutoff_time),
            )
            row = cursor.fetchone()

            return {
                "total_entries": row[0] or 0,
                "valid_entries": row[1] or 0,
                "expired_entries": (row[0] or 0) - (row[1] or 0),
                "average_health_score": round(row[2] or 0.0, 3),
                "ttl_seconds": self.ttl_seconds,
            }
