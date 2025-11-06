"""Tests for adaptive timeout functionality."""

import statistics
import time
from pathlib import Path

import pytest

from configstream.adaptive_timeout import AdaptiveTimeout, get_timeout_tracker


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test_timeout.db"
    return db_path


@pytest.fixture
def timeout_tracker(temp_db):
    """Create AdaptiveTimeout instance with temporary database."""
    return AdaptiveTimeout(db_path=temp_db, default_timeout=30)


def test_adaptive_timeout_initialization(timeout_tracker, temp_db):
    """Test that AdaptiveTimeout initializes correctly."""
    assert timeout_tracker.default_timeout == 30
    assert timeout_tracker.db_path == temp_db
    assert temp_db.exists()


def test_get_timeout_returns_default_for_new_source(timeout_tracker):
    """Test that default timeout is returned for unknown sources."""
    timeout = timeout_tracker.get_timeout("https://example.com")

    assert timeout == 30


def test_get_timeout_returns_adaptive_value_after_learning(timeout_tracker):
    """Test that adaptive timeout is calculated from historical data."""
    source = "https://example.com"

    # Record multiple fetch times
    timeout_tracker.record(source, 5.0)
    timeout_tracker.record(source, 6.0)
    timeout_tracker.record(source, 7.0)

    timeout = timeout_tracker.get_timeout(source)

    # Should be ~2x average (12s), clamped to 10-60 range
    expected = int(statistics.mean([5.0, 6.0, 7.0]) * 2)
    assert timeout == expected
    assert 10 <= timeout <= 60


def test_get_timeout_respects_minimum_bound(timeout_tracker):
    """Test that timeout is at least 10 seconds."""
    source = "https://fast-source.com"

    # Record very fast fetch times
    timeout_tracker.record(source, 0.5)
    timeout_tracker.record(source, 1.0)

    timeout = timeout_tracker.get_timeout(source)

    assert timeout == 10  # Minimum


def test_get_timeout_respects_maximum_bound(timeout_tracker):
    """Test that timeout is at most 60 seconds."""
    source = "https://slow-source.com"

    # Record very slow fetch times
    timeout_tracker.record(source, 40.0)
    timeout_tracker.record(source, 50.0)

    timeout = timeout_tracker.get_timeout(source)

    assert timeout == 60  # Maximum


def test_record_stores_fetch_duration(timeout_tracker):
    """Test that record stores fetch duration in database."""
    source = "https://example.com"

    timeout_tracker.record(source, 10.5)

    # Verify it's stored by getting adaptive timeout
    timeout = timeout_tracker.get_timeout(source)
    assert timeout == 21  # 10.5 * 2 = 21


def test_record_maintains_limited_history(timeout_tracker):
    """Test that only last 50 entries are kept per source."""
    source = "https://example.com"

    # Record 60 entries
    for i in range(60):
        timeout_tracker.record(source, 5.0 + i * 0.1)

    # Check cache only has 50 entries
    assert len(timeout_tracker._cache[source]) == 50


def test_record_persistence_across_instances(temp_db):
    """Test that recorded data persists across instances."""
    source = "https://example.com"

    # Create first instance and record data
    tracker1 = AdaptiveTimeout(db_path=temp_db)
    tracker1.record(source, 15.0)

    # Create second instance and verify data is loaded
    tracker2 = AdaptiveTimeout(db_path=temp_db)
    timeout = tracker2.get_timeout(source)

    assert timeout == 30  # 15.0 * 2 = 30


def test_cleanup_old_entries_removes_expired_data(timeout_tracker):
    """Test that cleanup removes old entries."""
    source = "https://example.com"

    # Record data
    timeout_tracker.record(source, 10.0)

    # Manually set old timestamp in database
    import sqlite3

    with sqlite3.connect(timeout_tracker.db_path) as conn:
        # Set timestamp to 31 days ago
        old_timestamp = int(time.time() - (31 * 24 * 60 * 60))
        conn.execute(
            "UPDATE timeout_history SET timestamp = ? WHERE source = ?",
            (old_timestamp, source),
        )
        conn.commit()

    # Run cleanup with 30-day retention
    deleted = timeout_tracker.cleanup_old_entries(days=30)

    assert deleted == 1


def test_cleanup_old_entries_keeps_recent_data(timeout_tracker):
    """Test that cleanup preserves recent data."""
    source = "https://example.com"

    # Record recent data
    timeout_tracker.record(source, 10.0)

    # Run cleanup
    deleted = timeout_tracker.cleanup_old_entries(days=30)

    assert deleted == 0
    # Data should still be accessible
    timeout = timeout_tracker.get_timeout(source)
    assert timeout == 20


def test_get_statistics_returns_correct_info(timeout_tracker):
    """Test that get_statistics returns correct information."""
    # Record data for multiple sources
    timeout_tracker.record("https://fast.com", 2.0)
    timeout_tracker.record("https://slow.com", 30.0)

    stats = timeout_tracker.get_statistics()

    assert stats["total_sources"] == 2
    assert stats["total_samples"] == 2
    assert stats["min_timeout"] >= 10
    assert stats["max_timeout"] <= 60
    assert 10 <= stats["avg_timeout"] <= 60


def test_get_statistics_with_no_data(timeout_tracker):
    """Test statistics with no recorded data."""
    stats = timeout_tracker.get_statistics()

    assert stats["total_sources"] == 0
    assert stats["total_samples"] == 0
    assert stats["avg_timeout"] == 30  # Default


def test_get_statistics_calculates_average_correctly(timeout_tracker):
    """Test that average timeout is calculated correctly."""
    # Record data for multiple sources with known timeouts
    timeout_tracker.record("https://source1.com", 5.0)  # Timeout: 10
    timeout_tracker.record("https://source2.com", 15.0)  # Timeout: 30
    timeout_tracker.record("https://source3.com", 25.0)  # Timeout: 50

    stats = timeout_tracker.get_statistics()

    expected_avg = statistics.mean([10, 30, 50])
    assert abs(stats["avg_timeout"] - expected_avg) < 0.1


def test_cache_loading_from_database(temp_db):
    """Test that cache is loaded from database on initialization."""
    source = "https://example.com"

    # Create instance and record data
    tracker1 = AdaptiveTimeout(db_path=temp_db)
    tracker1.record(source, 10.0)
    tracker1.record(source, 12.0)

    # Create new instance
    tracker2 = AdaptiveTimeout(db_path=temp_db)

    # Verify cache was loaded
    assert source in tracker2._cache
    # May have more or less depending on cleanup
    assert len(tracker2._cache[source]) >= 1


def test_get_timeout_with_statistics_error(timeout_tracker):
    """Test handling of statistics calculation errors."""
    source = "https://example.com"

    # Create invalid state (should not happen in practice)
    timeout_tracker._cache[source] = []

    # Should return default timeout
    timeout = timeout_tracker.get_timeout(source)

    assert timeout == 30  # Default


def test_get_timeout_tracker_singleton():
    """Test that get_timeout_tracker returns singleton instance."""
    tracker1 = get_timeout_tracker()
    tracker2 = get_timeout_tracker()

    assert tracker1 is tracker2


def test_record_with_multiple_sources(timeout_tracker):
    """Test recording data for multiple sources."""
    sources = [f"https://source{i}.com" for i in range(5)]

    for i, source in enumerate(sources):
        timeout_tracker.record(source, 5.0 + i)

    # Verify each source has adaptive timeout
    for i, source in enumerate(sources):
        timeout = timeout_tracker.get_timeout(source)
        expected = int((5.0 + i) * 2)
        expected = max(10, min(expected, 60))
        assert timeout == expected


def test_adaptive_timeout_uses_recent_samples(timeout_tracker):
    """Test that only recent samples (last 10) are used for calculation."""
    source = "https://example.com"

    # Record 15 samples with increasing durations
    for i in range(15):
        timeout_tracker.record(source, i + 1.0)

    # Get timeout (should use last 10 samples: 6-15)
    timeout = timeout_tracker.get_timeout(source)

    # Last 10 samples: [6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    # Average: 10.5, * 2 = 21
    assert timeout == 21


def test_database_error_handling(tmp_path):
    """Test graceful handling of database errors."""
    # Use invalid path that can't be created
    invalid_path = tmp_path / "nonexistent" / "dir" / "db.db"

    # Should not raise exception
    tracker = AdaptiveTimeout(db_path=invalid_path)

    # Should still work with in-memory cache
    tracker.record("https://example.com", 10.0)
    # Just verify no exception is raised
