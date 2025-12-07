"""
Storage module for Source Quality.
Handles SQLite interactions.
"""

import sqlite3
import logging
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, cast

logger = logging.getLogger(__name__)


class QualityStorage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._thread_local = threading.local()  # per-thread storage
        self._lock = threading.Lock()
        with self._lock:
            self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        # Each thread uses its own connection to avoid cross-thread contention.
        conn = getattr(self._thread_local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=True, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._thread_local.conn = conn
        return cast(sqlite3.Connection, conn)

    def _init_db(self):
        """Initialize the SQLite schema."""
        try:
            conn = self._get_conn()
            # Main stats table
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

            # Migration check for trust_score
            cursor = conn.execute("PRAGMA table_info(source_stats)")
            columns = [info[1] for info in cursor.fetchall()]
            if "trust_score" not in columns:
                conn.execute(
                    "ALTER TABLE source_stats ADD COLUMN trust_score REAL DEFAULT 50.0"
                )

            # History table for detailed run tracing
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    duration_ms REAL DEFAULT 0.0,
                    fetched_count INTEGER DEFAULT 0,
                    working_count INTEGER DEFAULT 0,
                    geoip_json TEXT DEFAULT '{}',
                    failure_modes_json TEXT DEFAULT '{}',
                    batch_source TEXT,
                    FOREIGN KEY(url) REFERENCES source_stats(url)
                )
                """
            )

            conn.commit()
        except Exception as e:
            logger.error(f"Failed to init source quality DB: {e}")

    def close(self):
        # Close current thread's connection
        conn = getattr(self._thread_local, "conn", None)
        if conn:
            conn.close()
            self._thread_local.conn = None

    def get_source_state(self, url: str) -> Optional[Tuple[Any, ...]]:
        """Get state for a source: (status, last_checked, consecutive_failures, reliability_score)."""
        with self._lock:
            try:
                conn = self._get_conn()
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
        with self._lock:
            try:
                conn = self._get_conn()
                row = conn.execute(
                    "SELECT trust_score FROM source_stats WHERE url = ?", (url,)
                ).fetchone()
                return row[0] if row else 50.0
            except Exception:
                return 50.0

    def upsert_stats(self, url: str, stats: Dict[str, Any]):
        """Insert or Update source stats."""
        with self._lock:
            try:
                conn = self._get_conn()
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

    def record_run(self, url: str, run_data: Dict[str, Any]):
        """Record a single run detail."""
        with self._lock:
            try:
                conn = self._get_conn()
                conn.execute(
                    """
                    INSERT INTO source_runs
                    (url, timestamp, duration_ms, fetched_count, working_count, geoip_json, failure_modes_json, batch_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        url,
                        run_data["timestamp"],
                        run_data["duration_ms"],
                        run_data["fetched_count"],
                        run_data["working_count"],
                        run_data.get("geoip_json", "{}"),
                        run_data.get("failure_modes_json", "{}"),
                        run_data.get("batch_source", None),
                    ),
                )
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to record run for {url}: {e}")

    def merge_from(self, other_db_path: Path):
        """Merge another DB into this one."""
        if not other_db_path.exists():
            return

        # Acquire lock to ensure we don't merge while other threads are writing
        with self._lock:
            try:
                # Note: We create new connections here, which is fine as long as we hold the lock
                # preventing other threads from using self._conn to write.
                with (
                    sqlite3.connect(other_db_path) as src,
                    sqlite3.connect(self.db_path) as dst,
                ):
                    src.execute("PRAGMA journal_mode=WAL")
                    dst.execute("PRAGMA journal_mode=WAL")

                # Merge source_stats
                rows = src.execute("SELECT * FROM source_stats").fetchall()
                if rows:
                    cursor = src.execute("SELECT * FROM source_stats LIMIT 1")
                    columns = [d[0] for d in cursor.description]
                    placeholders = ",".join(["?"] * len(columns))
                    url_idx = columns.index("url")
                    last_checked_idx = (
                        columns.index("last_checked")
                        if "last_checked" in columns
                        else -1
                    )

                    for row in rows:
                        url = row[url_idx]
                        last_checked = (
                            row[last_checked_idx] if last_checked_idx >= 0 else 0
                        )

                        existing = dst.execute(
                            "SELECT last_checked FROM source_stats WHERE url = ?",
                            (url,),
                        ).fetchone()

                        if not existing:
                            dst.execute(
                                f"INSERT INTO source_stats VALUES ({placeholders})", row
                            )
                        elif existing[0] < last_checked:
                            dst.execute(
                                "DELETE FROM source_stats WHERE url = ?", (url,)
                            )
                            dst.execute(
                                f"INSERT INTO source_stats VALUES ({placeholders})", row
                            )

                    # Merge source_runs
                    try:
                        run_rows = src.execute("SELECT * FROM source_runs").fetchall()
                        if run_rows:
                            cursor = src.execute("SELECT * FROM source_runs LIMIT 1")
                            columns = [d[0] for d in cursor.description]
                            # Remove 'id' from columns/values since it's auto-increment
                            cols_no_id = [c for c in columns if c != "id"]
                            placeholders = ",".join(["?"] * len(cols_no_id))
                            # Indices for data without ID
                            indices = [i for i, c in enumerate(columns) if c != "id"]

                            for row in run_rows:
                                data = [row[i] for i in indices]
                                dst.execute(
                                    f"INSERT INTO source_runs ({','.join(cols_no_id)}) VALUES ({placeholders})",
                                    data,
                                )
                    except sqlite3.OperationalError:
                        # 'source_runs' table missing in legacy schema versions.
                        # Ignore during merging; schema migration is handled in init.
                        pass

                    dst.commit()
                    logger.info(f"Merged source stats from {other_db_path}")
            except Exception as e:
                logger.error(f"Failed to merge source quality DB {other_db_path}: {e}")
