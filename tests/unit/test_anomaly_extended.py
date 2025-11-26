import pytest
import sqlite3
from unittest.mock import patch
from configstream.anomaly import AnomalyDetector


@pytest.fixture
def detector(tmp_path):
    db_path = tmp_path / "anomaly.db"
    return AnomalyDetector(db_path)


def test_init(detector):
    assert detector.db_path.exists()
    conn = sqlite3.connect(detector.db_path)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='history'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_is_safe_small_batch(detector):
    safe, reason = detector.is_safe("http://test", 5)
    assert safe is True
    assert reason == "Small Batch"


def test_is_safe_new_source(detector):
    safe, reason = detector.is_safe("http://new", 100)
    assert safe is True
    assert reason == "New Source"


def test_record_and_safe(detector):
    url = "http://test"
    # Record baseline
    # We need to bypass record's pruning potentially or just insert enough
    # Actually record commits.

    # To trigger Z-Score or IF, we need history.
    # 10 records of 100
    for i in range(10):
        detector.record(url, 100)

    # Check if records exist
    with sqlite3.connect(detector.db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM history WHERE url=?", (url,)
        ).fetchone()[0]
    assert count == 10

    # Average is 100.
    # Spike to 1000 should be caught.

    safe, reason = detector.is_safe(url, 1000)

    # If it fails, it might be because avg > 10 logic isn't triggered or stdev is 0
    # If stdev is 0 (all 100), Z-Score logic handles it?
    # Code says: if stdev > 0 ... else if current > avg * 3 ...
    # 1000 > 300, so should return False.

    assert safe is False
    assert "Spike" in reason


def test_is_safe_isolation_forest(detector):
    url = "http://test"
    # Seed enough data for IF (>= 15)
    # Using exact 100 creates 0 variance, IF might behave weirdly or fine.
    # Let's add noise
    for i in range(20):
        detector.record(url, 100 + (i % 5))

    # Test outlier
    safe, reason = detector.is_safe(url, 1000)
    assert safe is False
    assert "Isolation Forest" in reason or "Spike" in reason


def test_massive_spike_small_source(detector):
    url = "http://small"
    # Avg <= 10
    for _ in range(10):
        detector.record(url, 5)

    safe, reason = detector.is_safe(url, 250)
    assert safe is False
    assert "Massive Spike" in reason


def test_check_subnet_flood(detector):
    proxies = [{"server": "1.1.1.1"}] * 10
    assert detector.check_subnet_flood(proxies) is False

    proxies = []
    for i in range(60):
        proxies.append({"server": f"{i}.1.1.1"})
    assert detector.check_subnet_flood(proxies) is False

    proxies = [{"server": "1.2.3.4"}] * 95
    proxies.extend([{"server": "5.6.7.8"}] * 5)
    assert detector.check_subnet_flood(proxies) is True


def test_merge_from(detector, tmp_path):
    other_db = tmp_path / "other.db"
    other_detector = AnomalyDetector(other_db)
    other_detector.record("http://other", 50)

    detector.merge_from(other_db)

    conn = sqlite3.connect(detector.db_path)
    row = conn.execute("SELECT count FROM history WHERE url='http://other'").fetchone()
    assert row is not None
    assert row[0] == 50
    conn.close()


def test_record_pruning(detector):
    url = "http://prune"
    # Insert 110 records.
    # Note: pruning happens per insert.
    # We need to ensure timestamps are different or orderable.
    # The record function uses int(time.time()).
    # If we run this loop too fast, timestamps might be identical.

    with patch("time.time") as mock_time:
        for i in range(110):
            mock_time.return_value = 1000 + i
            detector.record(url, i)

    conn = sqlite3.connect(detector.db_path)
    count = conn.execute("SELECT COUNT(*) FROM history WHERE url=?", (url,)).fetchone()[
        0
    ]
    conn.close()

    # Pruning keeps last 100.
    assert count == 100


def test_fail_open_on_error(detector):
    # When the anomaly DB fails, we now fail OPEN to avoid blocking all sources.
    with patch("sqlite3.connect", side_effect=Exception("DB Error")):
        safe, reason = detector.is_safe("http://test", 100)
        assert safe is True
        assert "Fail Open" in reason
