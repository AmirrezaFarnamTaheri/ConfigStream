import pytest
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock
from configstream.source_quality import SourceQualityTracker


@pytest.fixture
def tracker_db(tmp_path):
    db_path = tmp_path / "source_quality.db"
    tracker = SourceQualityTracker(db_path)
    yield tracker
    # Cleanup handled by tmp_path


def test_source_quality_init(tracker_db):
    assert tracker_db.db_path.exists()
    with sqlite3.connect(tracker_db.db_path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='source_stats'"
        )
        assert cursor.fetchone() is not None


def test_source_quality_update_and_score(tracker_db):
    url = "https://example.com/proxies"

    # Initial update: 100 fetched, 50 working (50% reliability)
    tracker_db.update(url, 100, 50, diversity_score=0.5)

    score = tracker_db.get_source_score(url)
    assert score > 0

    # Check failure handling
    # 0 fetched (failure)
    tracker_db.update(url, 0, 0)

    with sqlite3.connect(tracker_db.db_path) as conn:
        row = conn.execute(
            "SELECT consecutive_failures FROM source_stats WHERE url = ?", (url,)
        ).fetchone()
        assert row[0] == 1


def test_should_fetch_cooldown(tracker_db):
    url = "https://fail.com/proxies"

    # Simulate failures
    for _ in range(5):
        tracker_db.update(url, 10, 0)  # 0 working

    # Should be in cooldown
    assert tracker_db.should_fetch(url) is False

    # Simulate success
    tracker_db.update(url, 10, 5)
    # Failures reset
    with sqlite3.connect(tracker_db.db_path) as conn:
        row = conn.execute(
            "SELECT consecutive_failures FROM source_stats WHERE url = ?", (url,)
        ).fetchone()
        assert row[0] == 0

    assert tracker_db.should_fetch(url) is True


def test_merge_from(tracker_db, tmp_path):
    other_db_path = tmp_path / "other.db"
    other_tracker = SourceQualityTracker(other_db_path)

    url = "https://merge.com"
    other_tracker.update(url, 100, 100)

    tracker_db.merge_from(other_db_path)

    score = tracker_db.get_source_score(url)
    assert score > 50  # Should have merged high score
