import sqlite3
import time
from pathlib import Path

import pytest

from configstream import diskqueue

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Provides a temporary path for the SQLite database."""
    return tmp_path / "test_queue.sqlite"


async def test_stale_job_recovery_on_connect(tmp_db_path: Path):
    """
    Verify that stale 'processing' jobs are moved back to 'new' on connection.
    """
    # Step 1: Manually set up a database with a stale job
    # We bypass the normal connect() to create the table and insert a stale record
    # without triggering the recovery logic.
    conn = sqlite3.connect(tmp_db_path)
    with conn:
        conn.executescript(diskqueue.CREATE_SQL)
        stale_time = int(time.time()) - 700  # 700 seconds ago, > 10 minutes
        conn.execute(
            """
            INSERT INTO jobs (id, payload, status, tries, updated_at)
            VALUES (?, ?, 'processing', 1, ?)
            """,
            ("stale_job_1", '{"data": "stale"}', stale_time),
        )
        # Also add a recent job that should NOT be recovered
        recent_time = int(time.time()) - 100  # 100 seconds ago
        conn.execute(
            """
            INSERT INTO jobs (id, payload, status, tries, updated_at)
            VALUES (?, ?, 'processing', 1, ?)
            """,
            ("recent_job_1", '{"data": "recent"}', recent_time),
        )
    conn.close()

    # Step 2: Connect using the production function, which should trigger recovery
    conn = diskqueue.connect(path=tmp_db_path)

    # Step 3: Verify the state of the jobs
    with conn:
        cursor = conn.execute("SELECT id, status, tries, updated_at FROM jobs ORDER BY id")
        rows = {row["id"]: dict(row) for row in cursor.fetchall()}

    # The recent job should be untouched
    assert rows["recent_job_1"]["status"] == "processing"
    assert rows["recent_job_1"]["tries"] == 1
    assert rows["recent_job_1"]["updated_at"] == recent_time

    # The stale job should be recovered
    assert rows["stale_job_1"]["status"] == "new"
    assert rows["stale_job_1"]["tries"] == 2  # Tries should be incremented
    assert rows["stale_job_1"]["updated_at"] > stale_time  # Timestamp updated
    assert rows["stale_job_1"]["updated_at"] >= int(time.time()) - 5  # Check if it's recent


async def test_busy_timeout_prevents_locking_errors(tmp_db_path: Path):
    """
    Verify that the `busy_timeout` pragma prevents `database is locked` errors
    during concurrent write attempts.
    """
    import threading
    import queue

    # This queue will be used to signal when the first thread has locked the DB
    lock_acquired = queue.Queue()
    # This queue will hold exceptions from the threads
    errors = queue.Queue()

    def long_running_writer():
        """Connects, starts a long transaction to lock the DB, and signals."""
        try:
            conn = diskqueue.connect(path=tmp_db_path)
            with conn:
                # Begin a deferred transaction; the lock is acquired on the first write
                conn.execute("BEGIN DEFERRED")
                diskqueue.enqueue_many(conn, [("job1", {"d": 1})])
                lock_acquired.put(True)  # Signal that the lock is held
                time.sleep(0.5)  # Hold the lock
                # Transaction is committed on exiting 'with'
        except Exception as e:
            errors.put(e)

    def concurrent_writer():
        """Waits for the lock, then tries to write. Should not fail."""
        try:
            lock_acquired.get(timeout=2)  # Wait for the signal
            conn = diskqueue.connect(path=tmp_db_path)
            # This write will block until the other transaction finishes,
            # but it should not raise an exception due to busy_timeout.
            diskqueue.enqueue_many(conn, [("job2", {"d": 2})])
        except Exception as e:
            errors.put(e)

    # Run both threads
    t1 = threading.Thread(target=long_running_writer)
    t2 = threading.Thread(target=concurrent_writer)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    # Check if any exceptions were put in the queue
    if not errors.empty():
        raise errors.get()

    # Verify that both writes succeeded
    conn = diskqueue.connect(path=tmp_db_path)
    with conn:
        count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    assert count == 2, "Both writes should have completed successfully"
