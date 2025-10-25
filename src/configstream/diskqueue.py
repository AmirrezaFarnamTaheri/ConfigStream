"""SQLite-backed job queue used to avoid unbounded memory usage."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Iterable, Iterator, List, Tuple

from .async_file_ops import ensure_directory

DEFAULT_DB_PATH = Path("state/pipeline-jobs.sqlite")

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    tries INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or DEFAULT_DB_PATH
    ensure_directory(db_path.parent)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Enable WAL mode and performance optimizations
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=268435456")  # 256 MB
    conn.execute("PRAGMA cache_size=-80000")  # ~80 MB cache

    with conn:
        conn.executescript(CREATE_SQL)
    return conn


def enqueue_many(conn: sqlite3.Connection, items: Iterable[Tuple[str, dict]]) -> None:
    now = int(time.time())
    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO jobs (id, payload, updated_at) VALUES (?, ?, ?)",
            ((item_id, json.dumps(payload), now) for item_id, payload in items),
        )


def take_batch(conn: sqlite3.Connection, limit: int = 500) -> List[Tuple[str, dict]]:
    now = int(time.time())
    with conn:
        rows = conn.execute(
            "SELECT id, payload FROM jobs WHERE status = 'new' ORDER BY updated_at ASC LIMIT ?",
            (limit,),
        ).fetchall()
        if not rows:
            return []
        conn.executemany(
            "UPDATE jobs SET status = 'processing', tries = tries + 1, updated_at = ? WHERE id = ?",
            ((now, row["id"]) for row in rows),
        )
    return [(row["id"], json.loads(row["payload"])) for row in rows]


def finish(conn: sqlite3.Connection, ids: Iterable[str]) -> None:
    with conn:
        conn.executemany("DELETE FROM jobs WHERE id = ?", ((id_,) for id_ in ids))


def requeue(conn: sqlite3.Connection, ids: Iterable[str]) -> None:
    now = int(time.time())
    with conn:
        conn.executemany(
            "UPDATE jobs SET status = 'new', updated_at = ? WHERE id = ?",
            ((now, id_) for id_ in ids),
        )


def iter_all(conn: sqlite3.Connection) -> Iterator[dict]:
    cursor = conn.execute("SELECT payload FROM jobs WHERE status != 'processing'")
    for row in cursor:
        yield json.loads(row[0])


def clear(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute("DELETE FROM jobs")
