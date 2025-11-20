"""
Source Quality Tracker.
Grades sources based on historical yield and validity rates.
Automatically manages cooldowns for failing sources.
"""

import sqlite3
import logging
import math
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SourceQualityTracker:
    def __init__(self, db_path: Path = Path("data/source_quality.db")):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite schema for tracking source reliability."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
CREATE TABLE IF NOT EXISTS source_stats (
    url TEXT PRIMARY KEY,
    total_fetched INTEGER DEFAULT 0,
    total_working INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    last_checked INTEGER DEFAULT 0,
    reliability_score REAL DEFAULT 100.0,
    status TEXT DEFAULT 'active'
)
"""
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to init source quality DB: {e}")

    def should_fetch(self, url: str) -> bool:
        """
        Decide if a source should be fetched based on its cooldown status.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT status, last_checked, consecutive_failures FROM source_stats WHERE url = ?",
                    (url,),
                ).fetchone()

                if not row:
                    return True  # New source, always fetch

                status, last_ts, failures = row

                if status == "disabled":
                    return False

                # Exponential Backoff Logic
                # 0 failures -> 0 wait
                # 1 failure -> 1 hour wait
                # 2 failures -> 4 hour wait
                # 3 failures -> 8 hour wait
                # ... capped at 48 hours
                cooldown_hours = min(48, math.pow(2, failures)) if failures > 0 else 0

                # Calculate when the next allowed fetch is
                next_allowed = datetime.fromtimestamp(last_ts) + timedelta(
                    hours=cooldown_hours
                )

                if datetime.now() < next_allowed:
                    # Log only periodically to reduce noise
                    logger.debug(
                        f"Skipping {url} (Cooldown until {next_allowed.strftime('%H:%M')})"
                    )
                    return False

                return True

        except Exception as e:
            logger.warning(f"Error checking source quality for {url}: {e}")
            return True  # Fail open

    def update(self, url: str, fetched_count: int, working_count: int):
        """
        Update the stats for a source after a pipeline run.

        Args:
            url: The source URL
            fetched_count: How many valid config lines were parsed
            working_count: How many proxies actually passed the tests
        """
        now = int(datetime.now().timestamp())
        # We consider it a failure if we fetched content but NOTHING worked
        # If fetched_count is 0, it might just be empty/network error, also a failure
        is_failure = working_count == 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT total_fetched, total_working, consecutive_failures FROM source_stats WHERE url = ?",
                    (url,),
                ).fetchone()

                if row:
                    tf, tw, cf = row
                    new_tf = tf + fetched_count
                    new_tw = tw + working_count
                    # Reset consecutive failures if we got at least one working proxy
                    new_cf = cf + 1 if is_failure else 0

                    # Calculate Score: Simple percentage
                    score = (new_tw / new_tf * 100) if new_tf > 0 else 0.0

                    conn.execute(
                        """
                        UPDATE source_stats
                        SET total_fetched=?, total_working=?, consecutive_failures=?,
                        last_checked=?, reliability_score=?
                        WHERE url=?
                        """,
                        (new_tf, new_tw, new_cf, now, score, url),
                    )
                else:
                    # First time seeing this source
                    score = (
                        (working_count / fetched_count * 100)
                        if fetched_count > 0
                        else 0.0
                    )
                    conn.execute(
                        """
                        INSERT INTO source_stats
                        (url, total_fetched, total_working, consecutive_failures, last_checked, reliability_score)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            url,
                            fetched_count,
                            working_count,
                            1 if is_failure else 0,
                            now,
                            score,
                        ),
                    )

                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update source stats for {url}: {e}")

    def get_source_score(self, url: str) -> float:
        """Get the current reliability score for a source."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT reliability_score FROM source_stats WHERE url = ?", (url,)
                ).fetchone()
                return row[0] if row else 50.0  # Default to neutral
        except Exception:
            return 50.0
