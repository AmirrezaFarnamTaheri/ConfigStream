# SPDX-License-Identifier: AGPL-3.0-or-later
"""Transactional, idempotent SQLite storage for source quality evidence."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, cast

from configstream.security_validator import SecurityValidator

logger = logging.getLogger(__name__)
SCHEMA_VERSION = 4


class QualityStorageError(RuntimeError):
    """Raised when quality state cannot be read or committed safely."""


def _safe_message(value: object) -> str:
    return SecurityValidator.sanitize_log_message(str(value))


class QualityStorage:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._thread_local = threading.local()
        self._lock = threading.RLock()
        self._all_connections: set[sqlite3.Connection] = set()
        self._generation = 0
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        return self._get_conn()

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._thread_local, "conn", None)
        if (
            conn is not None
            and getattr(self._thread_local, "generation", -1) != self._generation
        ):
            self._thread_local.conn = None
            conn = None
        if conn is None:
            try:
                conn = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=20,
                    isolation_level=None,
                )
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=FULL")
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute("PRAGMA busy_timeout=20000")
            except sqlite3.Error as exc:
                raise QualityStorageError(
                    f"failed to open quality database {self.db_path}: {_safe_message(exc)}"
                ) from exc
            self._thread_local.conn = conn
            self._thread_local.generation = self._generation
            with self._lock:
                self._all_connections.add(conn)
        return cast(sqlite3.Connection, conn)

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = self._get_conn()
            depth = int(getattr(self._thread_local, "transaction_depth", 0))
            self._thread_local.transaction_depth = depth + 1
            try:
                if depth == 0:
                    conn.execute("BEGIN IMMEDIATE")
                yield conn
                if depth == 0:
                    conn.commit()
            except Exception:
                if depth == 0:
                    conn.rollback()
                raise
            finally:
                self._thread_local.transaction_depth = depth

    @staticmethod
    def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
        return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}

    def _init_db(self) -> None:
        try:
            with self._transaction() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                    """)
                stored_version = conn.execute(
                    "SELECT value FROM schema_meta WHERE key = 'schema_version'"
                ).fetchone()
                if (
                    stored_version is not None
                    and int(stored_version[0]) > SCHEMA_VERSION
                ):
                    raise QualityStorageError(
                        "quality database schema is newer than this application"
                    )

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS source_stats (
                        url TEXT PRIMARY KEY,
                        total_fetched INTEGER NOT NULL DEFAULT 0,
                        total_working INTEGER NOT NULL DEFAULT 0,
                        consecutive_failures INTEGER NOT NULL DEFAULT 0,
                        last_checked INTEGER NOT NULL DEFAULT 0,
                        reliability_score REAL NOT NULL DEFAULT 100.0,
                        diversity_score REAL NOT NULL DEFAULT 0.0,
                        trust_score REAL NOT NULL DEFAULT 50.0,
                        status TEXT NOT NULL DEFAULT 'active',
                        state_sequence INTEGER NOT NULL DEFAULT 0
                    )
                    """)
                source_columns = self._columns(conn, "source_stats")
                if "trust_score" not in source_columns:
                    conn.execute(
                        "ALTER TABLE source_stats ADD COLUMN trust_score REAL NOT NULL DEFAULT 50.0"
                    )
                if "status" not in source_columns:
                    conn.execute(
                        "ALTER TABLE source_stats ADD COLUMN status TEXT NOT NULL DEFAULT 'active'"
                    )
                if "state_sequence" not in source_columns:
                    conn.execute(
                        "ALTER TABLE source_stats ADD COLUMN state_sequence INTEGER NOT NULL DEFAULT 0"
                    )

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS source_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_key TEXT,
                        url TEXT NOT NULL,
                        timestamp INTEGER NOT NULL,
                        duration_ms REAL NOT NULL DEFAULT 0.0,
                        fetched_count INTEGER NOT NULL DEFAULT 0,
                        working_count INTEGER NOT NULL DEFAULT 0,
                        geoip_json TEXT NOT NULL DEFAULT '{}',
                        failure_modes_json TEXT NOT NULL DEFAULT '{}',
                        batch_source TEXT,
                        FOREIGN KEY(url) REFERENCES source_stats(url)
                    )
                    """)
                run_columns = self._columns(conn, "source_runs")
                if "run_key" not in run_columns:
                    conn.execute("ALTER TABLE source_runs ADD COLUMN run_key TEXT")
                conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_source_runs_run_key "
                    "ON source_runs(run_key) WHERE run_key IS NOT NULL"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_source_runs_url_ts "
                    "ON source_runs(url, timestamp)"
                )

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS proxy_history (
                        proxy_id TEXT NOT NULL,
                        timestamp INTEGER NOT NULL,
                        is_working INTEGER NOT NULL,
                        latency REAL,
                        country_code TEXT,
                        session_id TEXT,
                        failure_reason TEXT,
                        event_key TEXT
                    )
                    """)
                history_columns = self._columns(conn, "proxy_history")
                if "event_key" not in history_columns:
                    conn.execute("ALTER TABLE proxy_history ADD COLUMN event_key TEXT")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_proxy_history_id "
                    "ON proxy_history(proxy_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_proxy_history_ts "
                    "ON proxy_history(timestamp)"
                )
                conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_proxy_history_event_key "
                    "ON proxy_history(event_key) WHERE event_key IS NOT NULL"
                )
                conn.execute(
                    "INSERT INTO schema_meta(key, value) VALUES('schema_version', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (str(SCHEMA_VERSION),),
                )
        except Exception as exc:
            if isinstance(exc, QualityStorageError):
                raise
            raise QualityStorageError(
                f"failed to initialize quality database {self.db_path}: {_safe_message(exc)}"
            ) from exc

    def close(self) -> None:
        conn = getattr(self._thread_local, "conn", None)
        if conn is not None:
            conn.close()
            self._thread_local.conn = None
        with self._lock:
            self._generation += 1
            for tracked in self._all_connections:
                try:
                    tracked.close()
                except sqlite3.Error:
                    pass
            self._all_connections.clear()

    def execute_write(self, sql: str, params: Tuple = ()) -> None:
        try:
            with self._transaction() as conn:
                conn.execute(sql, params)
        except Exception as exc:
            raise QualityStorageError(
                f"quality DB write failed: {_safe_message(exc)}"
            ) from exc

    def execute_write_many(self, sql: str, params_list: List[Tuple]) -> None:
        if not params_list:
            return
        try:
            with self._transaction() as conn:
                conn.executemany(sql, params_list)
        except Exception as exc:
            raise QualityStorageError(
                f"quality DB batch write failed: {_safe_message(exc)}"
            ) from exc

    def get_source_state(self, url: str) -> Optional[Tuple[Any, ...]]:
        try:
            with self._lock:
                row = (
                    self._get_conn()
                    .execute(
                        """
                    SELECT status, last_checked, consecutive_failures,
                           reliability_score, total_fetched, total_working
                    FROM source_stats WHERE url = ?
                    """,
                        (url,),
                    )
                    .fetchone()
                )
            return tuple(row) if row is not None else None
        except sqlite3.Error as exc:
            raise QualityStorageError(
                f"failed to read source state for {_safe_message(url)}: {_safe_message(exc)}"
            ) from exc

    def get_trust_score(self, url: str) -> float:
        try:
            with self._lock:
                row = (
                    self._get_conn()
                    .execute(
                        "SELECT trust_score FROM source_stats WHERE url = ?", (url,)
                    )
                    .fetchone()
                )
            return float(row[0]) if row else 50.0
        except sqlite3.Error as exc:
            raise QualityStorageError(
                f"failed to read trust score for {_safe_message(url)}: {_safe_message(exc)}"
            ) from exc

    def upsert_stats(self, url: str, stats: Dict[str, Any]) -> None:
        defaults: Dict[str, Any] = {
            "total_fetched": 0,
            "total_working": 0,
            "consecutive_failures": 0,
            "last_checked": 0,
            "reliability_score": 100.0,
            "diversity_score": 0.0,
            "trust_score": 50.0,
            "status": "active",
            "state_sequence": 0,
        }
        try:
            with self._transaction() as conn:
                existing = conn.execute(
                    """
                    SELECT total_fetched, total_working, consecutive_failures,
                           last_checked, reliability_score, diversity_score,
                           trust_score, status, state_sequence
                    FROM source_stats WHERE url = ?
                    """,
                    (url,),
                ).fetchone()
                if existing:
                    current = {
                        "total_fetched": existing[0],
                        "total_working": existing[1],
                        "consecutive_failures": existing[2],
                        "last_checked": existing[3],
                        "reliability_score": existing[4],
                        "diversity_score": existing[5],
                        "trust_score": existing[6],
                        "status": existing[7],
                        "state_sequence": existing[8],
                    }
                    merged = {**current, **stats}
                    merged["state_sequence"] = max(
                        int(current["state_sequence"]) + 1,
                        int(stats.get("state_sequence", 0)),
                    )
                else:
                    merged = {**defaults, **stats}
                    merged["state_sequence"] = max(
                        1, int(stats.get("state_sequence", 0))
                    )

                conn.execute(
                    """
                    INSERT INTO source_stats(
                        url, total_fetched, total_working, consecutive_failures,
                        last_checked, reliability_score, diversity_score,
                        trust_score, status, state_sequence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        total_fetched=excluded.total_fetched,
                        total_working=excluded.total_working,
                        consecutive_failures=excluded.consecutive_failures,
                        last_checked=excluded.last_checked,
                        reliability_score=excluded.reliability_score,
                        diversity_score=excluded.diversity_score,
                        trust_score=excluded.trust_score,
                        status=excluded.status,
                        state_sequence=excluded.state_sequence
                    """,
                    (
                        url,
                        int(merged["total_fetched"]),
                        int(merged["total_working"]),
                        int(merged["consecutive_failures"]),
                        int(merged["last_checked"]),
                        float(merged["reliability_score"]),
                        float(merged["diversity_score"]),
                        float(merged["trust_score"]),
                        str(merged["status"]),
                        int(merged["state_sequence"]),
                    ),
                )
        except Exception as exc:
            if isinstance(exc, QualityStorageError):
                raise
            raise QualityStorageError(
                f"failed to update stats for {_safe_message(url)}: {_safe_message(exc)}"
            ) from exc

    @staticmethod
    def _run_key(url: str, run_data: Dict[str, Any]) -> str:
        supplied = run_data.get("run_key") or run_data.get("event_id")
        if supplied:
            return str(supplied)
        canonical = json.dumps(
            {
                "url": url,
                "run_id": run_data.get("run_id"),
                "shard_id": run_data.get("shard_id"),
                "timestamp": run_data.get("timestamp"),
                "duration_ms": run_data.get("duration_ms", 0.0),
                "fetched_count": run_data.get("fetched_count", 0),
                "working_count": run_data.get("working_count", 0),
                "geoip_json": run_data.get("geoip_json", "{}"),
                "failure_modes_json": run_data.get("failure_modes_json", "{}"),
                "batch_source": run_data.get("batch_source"),
                "consumer_id": run_data.get("consumer_id"),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def record_run(self, url: str, run_data: Dict[str, Any]) -> bool:
        """Record a run once. Return False when the event was already applied."""

        run_key = self._run_key(url, run_data)
        try:
            with self._transaction() as conn:
                conn.execute(
                    "INSERT INTO source_stats(url) VALUES (?) "
                    "ON CONFLICT(url) DO NOTHING",
                    (url,),
                )
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO source_runs(
                        run_key, url, timestamp, duration_ms, fetched_count,
                        working_count, geoip_json, failure_modes_json, batch_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_key,
                        url,
                        int(run_data["timestamp"]),
                        float(run_data.get("duration_ms", 0.0)),
                        int(run_data.get("fetched_count", 0)),
                        int(run_data.get("working_count", 0)),
                        str(run_data.get("geoip_json", "{}")),
                        str(run_data.get("failure_modes_json", "{}")),
                        run_data.get("batch_source"),
                    ),
                )
                return cursor.rowcount == 1
        except Exception as exc:
            if isinstance(exc, QualityStorageError):
                raise
            raise QualityStorageError(
                f"failed to record run for {_safe_message(url)}: {_safe_message(exc)}"
            ) from exc

    def get_worst_performing(self, limit: int = 5) -> list[Dict[str, Any]]:
        if limit <= 0:
            return []
        try:
            with self._lock:
                rows = (
                    self._get_conn()
                    .execute(
                        """
                    SELECT url, reliability_score, consecutive_failures, status
                    FROM source_stats
                    WHERE reliability_score < 50 OR consecutive_failures > 0
                    ORDER BY consecutive_failures DESC, reliability_score ASC
                    LIMIT ?
                    """,
                        (limit,),
                    )
                    .fetchall()
                )
        except sqlite3.Error as exc:
            raise QualityStorageError(
                f"failed to query worst sources: {_safe_message(exc)}"
            ) from exc
        return [
            {
                "url": row[0],
                "score": row[1],
                "failures": row[2],
                "status": row[3],
                "last_failure_reason": (
                    "High Failures" if row[2] > 0 else "Low Reliability"
                ),
            }
            for row in rows
        ]

    def merge_from(self, other_db_path: Path) -> None:
        """Idempotently merge a shard database into this database."""

        other = Path(other_db_path)
        if not other.exists():
            return
        src: sqlite3.Connection | None = None
        try:
            src = sqlite3.connect(other)
            src.row_factory = sqlite3.Row
            with src:
                source_rows = src.execute("SELECT * FROM source_stats")
                try:
                    run_rows = src.execute("SELECT * FROM source_runs")
                except sqlite3.OperationalError:
                    run_rows = []
                try:
                    history_rows = src.execute("SELECT * FROM proxy_history")
                except sqlite3.OperationalError:
                    history_rows = []

            with self._transaction() as dst:
                for row in source_rows:
                    existing = dst.execute(
                        "SELECT state_sequence, last_checked FROM source_stats WHERE url = ?",
                        (row["url"],),
                    ).fetchone()
                    source_sequence = (
                        int(row["state_sequence"] or 0)
                        if "state_sequence" in row.keys()
                        else 0
                    )
                    source_checked = int(row["last_checked"] or 0)
                    if existing:
                        destination_order = (
                            int(existing[0] or 0),
                            int(existing[1] or 0),
                        )
                        source_order = (source_sequence, source_checked)
                        if source_order <= destination_order:
                            continue
                    dst.execute(
                        """
                        INSERT INTO source_stats(
                            url, total_fetched, total_working, consecutive_failures,
                            last_checked, reliability_score, diversity_score,
                            trust_score, status, state_sequence
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(url) DO UPDATE SET
                            total_fetched=excluded.total_fetched,
                            total_working=excluded.total_working,
                            consecutive_failures=excluded.consecutive_failures,
                            last_checked=excluded.last_checked,
                            reliability_score=excluded.reliability_score,
                            diversity_score=excluded.diversity_score,
                            trust_score=excluded.trust_score,
                            status=excluded.status,
                            state_sequence=excluded.state_sequence
                        """,
                        (
                            row["url"],
                            row["total_fetched"],
                            row["total_working"],
                            row["consecutive_failures"],
                            row["last_checked"],
                            row["reliability_score"],
                            row["diversity_score"],
                            row["trust_score"] if "trust_score" in row.keys() else 50.0,
                            row["status"] if "status" in row.keys() else "active",
                            source_sequence,
                        ),
                    )

                for row in run_rows:
                    data = dict(row)
                    run_url = str(data.get("url") or "")
                    if not run_url:
                        continue
                    dst.execute(
                        "INSERT INTO source_stats(url) VALUES (?) "
                        "ON CONFLICT(url) DO NOTHING",
                        (run_url,),
                    )
                    run_key = data.get("run_key") or self._run_key(run_url, data)
                    dst.execute(
                        """
                        INSERT OR IGNORE INTO source_runs(
                            run_key, url, timestamp, duration_ms, fetched_count,
                            working_count, geoip_json, failure_modes_json, batch_source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            run_key,
                            run_url,
                            data.get("timestamp"),
                            data.get("duration_ms", 0.0),
                            data.get("fetched_count", 0),
                            data.get("working_count", 0),
                            data.get("geoip_json", "{}"),
                            data.get("failure_modes_json", "{}"),
                            data.get("batch_source"),
                        ),
                    )

                for row in history_rows:
                    data = dict(row)
                    event_key = (
                        data.get("event_key")
                        or hashlib.sha256(
                            json.dumps(
                                {
                                    "proxy_id": data.get("proxy_id"),
                                    "timestamp": data.get("timestamp"),
                                    "session_id": data.get("session_id"),
                                    "is_working": data.get("is_working"),
                                    "failure_reason": data.get("failure_reason"),
                                },
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode("utf-8")
                        ).hexdigest()
                    )
                    dst.execute(
                        """
                        INSERT OR IGNORE INTO proxy_history(
                            proxy_id, timestamp, is_working, latency, country_code,
                            session_id, failure_reason, event_key
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            data.get("proxy_id"),
                            data.get("timestamp"),
                            data.get("is_working"),
                            data.get("latency"),
                            data.get("country_code"),
                            data.get("session_id"),
                            data.get("failure_reason"),
                            event_key,
                        ),
                    )
            logger.info("Idempotently merged source quality state from %s", other)
        except Exception as exc:
            if isinstance(exc, QualityStorageError):
                raise
            raise QualityStorageError(
                f"failed to merge source quality DB {other}: {_safe_message(exc)}"
            ) from exc
        finally:
            if src is not None:
                try:
                    src.close()
                except sqlite3.Error:
                    logger.debug(
                        "Failed to close merged source database", exc_info=True
                    )
