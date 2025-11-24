"""
Storage module for Source Quality.
Handles SQLite interactions.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class QualityStorage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS source_stats (
                        url TEXT PRIMARY KEY,
                        total_fetched INTEGER DEFAULT 0,
                        total_working INTEGER DEFAULT 0,
                        consecutive_failures INTEGER DEFAULT 0,
                        last_checked INTEGER DEFAULT 0,
                        reliability_score REAL DEFAULT 100.0,
                        diversity_score REAL DEFAULT 0.0,
                        trust_score REAL DEFAULT 50.0,
                        status TEXT DEFAULT 'active'
                    )
                    """
                )

                # Migration check
                cursor = conn.execute("PRAGMA table_info(source_stats)")
                columns = [info[1] for info in cursor.fetchall()]
                if "trust_score" not in columns:
                    conn.execute(
                        "ALTER TABLE source_stats ADD COLUMN trust_score REAL DEFAULT 50.0"
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to init source quality DB: {e}")

    def get_source_state(self, url: str) -> Optional[Tuple[Any, ...]]:
        """Get state for a source: (status, last_checked, consecutive_failures, reliability_score)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT status, last_checked, consecutive_failures, reliability_score, total_fetched, total_working FROM source_stats WHERE url = ?",
                    (url,),
                ).fetchone()
                return row  # type: ignore
        except Exception as e:
            logger.error(f"Failed to get source state for {url}: {e}")
            return None

    def get_trust_score(self, url: str) -> float:
        """Get trust score."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT trust_score FROM source_stats WHERE url = ?", (url,)
                ).fetchone()
                return row[0] if row else 50.0
        except Exception:
            return 50.0

    def upsert_stats(self, url: str, stats: Dict[str, Any]):
        """Insert or Update source stats."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if exists (handled by INSERT OR REPLACE or explicit check)
                # We use explicit check to be safe with partial updates if needed,
                # but here we usually update everything.
                # However, logic in original code was: SELECT first, then UPDATE or INSERT.

                # We can use INSERT OR REPLACE if we provide all columns, but we want to preserve 'status' if not provided
                # Let's assume stats contains updated values for metrics.

                # Check existence
                exists = conn.execute(
                    "SELECT 1 FROM source_stats WHERE url = ?", (url,)
                ).fetchone()

                if exists:
                    conn.execute(
                        """
                        UPDATE source_stats
                        SET total_fetched=?, total_working=?, consecutive_failures=?,
                        last_checked=?, reliability_score=?, diversity_score=?, trust_score=?
                        WHERE url=?
                        """,
                        (
                            stats["total_fetched"],
                            stats["total_working"],
                            stats["consecutive_failures"],
                            stats["last_checked"],
                            stats["reliability_score"],
                            stats["diversity_score"],
                            stats["trust_score"],
                            url,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO source_stats
                        (url, total_fetched, total_working, consecutive_failures, last_checked, reliability_score, diversity_score, trust_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            url,
                            stats["total_fetched"],
                            stats["total_working"],
                            stats["consecutive_failures"],
                            stats["last_checked"],
                            stats["reliability_score"],
                            stats["diversity_score"],
                            stats["trust_score"],
                        ),
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update stats for {url}: {e}")

    def merge_from(self, other_db_path: Path):
        """Merge another DB into this one."""
        if not other_db_path.exists():
            return

        try:
            with (
                sqlite3.connect(other_db_path) as src,
                sqlite3.connect(self.db_path) as dst,
            ):
                src.execute("PRAGMA journal_mode=WAL")
                dst.execute("PRAGMA journal_mode=WAL")

                rows = src.execute("SELECT * FROM source_stats").fetchall()
                cursor = src.execute("SELECT * FROM source_stats LIMIT 1")
                columns = [d[0] for d in cursor.description]
                placeholders = ",".join(["?"] * len(columns))

                for row in rows:
                    data = dict(zip(columns, row))
                    url = data["url"]
                    last_checked = data.get("last_checked", 0)

                    existing = dst.execute(
                        "SELECT last_checked FROM source_stats WHERE url = ?", (url,)
                    ).fetchone()

                    if not existing:
                        dst.execute(
                            f"INSERT INTO source_stats VALUES ({placeholders})", row
                        )
                    elif existing[0] < last_checked:
                        dst.execute("DELETE FROM source_stats WHERE url = ?", (url,))
                        dst.execute(
                            f"INSERT INTO source_stats VALUES ({placeholders})", row
                        )

                dst.commit()
                logger.info(f"Merged source stats from {other_db_path}")
        except Exception as e:
            logger.error(f"Failed to merge source quality DB {other_db_path}: {e}")
