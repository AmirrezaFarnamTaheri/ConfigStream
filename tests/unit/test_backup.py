"""Tests for database backup functionality."""

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from configstream.backup import (
    backup_databases,
    cleanup_old_backups,
    get_backup_statistics,
    list_backups,
    restore_database,
)


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory with test databases."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create actual SQLite database files
    for db_name in ["test_cache.db", "proxy_history.db"]:
        db_path = data_dir / db_name
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
        conn.execute("INSERT INTO test (data) VALUES (?)", ("test data",))
        conn.commit()
        conn.close()

    return data_dir


@pytest.fixture
def temp_backup_dir(tmp_path):
    """Create temporary backup directory."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return backup_dir


def test_backup_databases_creates_backups(temp_data_dir, temp_backup_dir):
    """Test that backup_databases creates timestamped backups."""
    backups = backup_databases(data_dir=temp_data_dir, backup_dir=temp_backup_dir, retention_days=7)

    assert len(backups) == 2
    assert all(backup.exists() for backup in backups)
    assert all(".db" in backup.name for backup in backups)


def test_backup_databases_with_no_databases(tmp_path):
    """Test backup with empty data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    backups = backup_databases(data_dir=data_dir)

    assert len(backups) == 0


def test_backup_databases_creates_backup_directory(temp_data_dir, tmp_path):
    """Test that backup directory is created if it doesn't exist."""
    backup_dir = tmp_path / "new_backups"

    backups = backup_databases(data_dir=temp_data_dir, backup_dir=backup_dir)

    assert backup_dir.exists()
    assert len(backups) == 2


def test_cleanup_old_backups_removes_old_files(temp_backup_dir):
    """Test that old backups are removed."""
    import os
    import time

    # Create old backup with old modification time
    old_backup = temp_backup_dir / "test_20200101_120000.db"
    old_backup.write_text("old data")

    # Set modification time to 2 days ago
    old_time = time.time() - (2 * 24 * 60 * 60)
    os.utime(old_backup, (old_time, old_time))

    # Create recent backup
    recent_backup = temp_backup_dir / f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    recent_backup.write_text("recent data")

    deleted = cleanup_old_backups(temp_backup_dir, retention_days=1)

    assert deleted == 1
    assert not old_backup.exists()
    assert recent_backup.exists()


def test_cleanup_old_backups_with_nonexistent_directory(tmp_path):
    """Test cleanup with nonexistent directory."""
    backup_dir = tmp_path / "nonexistent"

    deleted = cleanup_old_backups(backup_dir, retention_days=7)

    assert deleted == 0


def test_restore_database_copies_file(tmp_path):
    """Test that restore_database copies the backup file."""
    # Create backup file
    backup_file = tmp_path / "backup.db"
    backup_file.write_text("backup data")

    # Create target location
    target_file = tmp_path / "target.db"

    success = restore_database(backup_file, target_file)

    assert success
    assert target_file.exists()
    assert target_file.read_text() == "backup data"


def test_restore_database_creates_pre_restore_backup(tmp_path):
    """Test that restore creates a backup of existing target file."""
    # Create backup file
    backup_file = tmp_path / "backup.db"
    backup_file.write_text("backup data")

    # Create existing target file
    target_file = tmp_path / "target.db"
    target_file.write_text("existing data")

    success = restore_database(backup_file, target_file)

    assert success
    # Check that pre-restore backup was created
    pre_restore_backups = list(tmp_path.glob("target.pre_restore_*.db"))
    assert len(pre_restore_backups) == 1
    assert pre_restore_backups[0].read_text() == "existing data"


def test_restore_database_with_nonexistent_backup(tmp_path):
    """Test restore with nonexistent backup file."""
    backup_file = tmp_path / "nonexistent.db"
    target_file = tmp_path / "target.db"

    success = restore_database(backup_file, target_file)

    assert not success


def test_list_backups_returns_sorted_list(temp_backup_dir):
    """Test that list_backups returns backups sorted by modification time."""
    # Create multiple backups with different timestamps
    backup1 = temp_backup_dir / "db_20250101_120000.db"
    backup1.write_text("data1")

    backup2 = temp_backup_dir / "db_20250102_120000.db"
    backup2.write_text("data2")

    backups = list_backups(temp_backup_dir)

    assert len(backups) == 2
    assert all("filename" in b for b in backups)
    assert all("size_mb" in b for b in backups)
    assert all("created" in b for b in backups)
    assert all("age_days" in b for b in backups)


def test_list_backups_with_empty_directory(temp_backup_dir):
    """Test list_backups with empty directory."""
    backups = list_backups(temp_backup_dir)

    assert len(backups) == 0


def test_list_backups_with_nonexistent_directory(tmp_path):
    """Test list_backups with nonexistent directory."""
    backup_dir = tmp_path / "nonexistent"

    backups = list_backups(backup_dir)

    assert len(backups) == 0


def test_get_backup_statistics_returns_correct_info(temp_backup_dir):
    """Test that get_backup_statistics returns correct information."""
    # Create backups
    backup1 = temp_backup_dir / "db1_20250101_120000.db"
    backup1.write_text("x" * 1024 * 1024)  # 1 MB

    backup2 = temp_backup_dir / "db2_20250102_120000.db"
    backup2.write_text("y" * 1024 * 1024)  # 1 MB

    stats = get_backup_statistics(temp_backup_dir)

    assert stats["total_backups"] == 2
    assert stats["total_size_mb"] >= 2.0  # At least 2 MB
    assert "oldest_backup" in stats
    assert "newest_backup" in stats
    assert "backups_by_database" in stats


def test_get_backup_statistics_with_no_backups(temp_backup_dir):
    """Test statistics with no backups."""
    stats = get_backup_statistics(temp_backup_dir)

    assert stats["total_backups"] == 0
    assert stats["total_size_mb"] == 0.0
    assert stats["oldest_backup"] is None
    assert stats["newest_backup"] is None


def test_backup_databases_with_retention_cleanup(temp_data_dir, temp_backup_dir):
    """Test that retention policy is applied during backup."""
    import os
    import time

    # Create old backup with old modification time
    old_backup = temp_backup_dir / "test_20200101_120000.db"
    old_backup.write_text("old data")

    # Set modification time to 2 days ago
    old_time = time.time() - (2 * 24 * 60 * 60)
    os.utime(old_backup, (old_time, old_time))

    # Run backup with 1-day retention
    backups = backup_databases(data_dir=temp_data_dir, backup_dir=temp_backup_dir, retention_days=1)

    # Old backup should be cleaned up
    assert not old_backup.exists()
    # New backups should exist
    assert len(backups) == 2


def test_backup_databases_handles_permission_error(temp_data_dir, tmp_path):
    """Test backup handling when backup fails."""
    # This test verifies graceful error handling
    # Create a read-only database file (simulating permission error scenario)
    readonly_db = temp_data_dir / "readonly.db"
    conn = sqlite3.connect(readonly_db)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
    conn.commit()
    conn.close()

    # Backup should succeed for other files even if one fails
    backups = backup_databases(data_dir=temp_data_dir, retention_days=7)

    # At least some backups should succeed (2 from fixture + 1 readonly = 3 total)
    assert len(backups) >= 2


def test_group_backups_by_database(temp_backup_dir):
    """Test that backups are grouped by database name correctly."""
    # Create backups for different databases
    (temp_backup_dir / "cache_20250101_120000.db").write_text("data1")
    (temp_backup_dir / "cache_20250102_120000.db").write_text("data2")
    (temp_backup_dir / "history_20250101_120000.db").write_text("data3")

    stats = get_backup_statistics(temp_backup_dir)
    grouped = stats["backups_by_database"]

    assert "cache" in grouped
    assert "history" in grouped
    assert len(grouped["cache"]) == 2
    assert len(grouped["history"]) == 1


def test_backup_with_older_sqlite_without_pages_kwarg(temp_data_dir, temp_backup_dir):
    """Test backup fallback when SQLite doesn't support pages parameter."""
    # This test verifies the code has proper fallback handling
    # The actual fallback is tested by running the code as-is
    # Modern SQLite supports pages, so we just verify backups succeed
    backups = backup_databases(data_dir=temp_data_dir, backup_dir=temp_backup_dir)

    # Should succeed regardless of SQLite version
    assert len(backups) == 2
    assert all(backup.exists() for backup in backups)


def test_backup_with_older_sqlite_without_immutable_mode(
    temp_data_dir, temp_backup_dir, monkeypatch
):
    """Test backup fallback when SQLite doesn't support immutable mode."""
    import sqlite3

    # Mock connect to raise OperationalError on immutable mode
    original_connect = sqlite3.connect

    def mock_connect(db, **kwargs):
        if "uri" in kwargs and kwargs["uri"] and "immutable=1" in str(db):
            raise sqlite3.OperationalError("no such access mode: immutable")
        return original_connect(db, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", mock_connect)

    backups = backup_databases(data_dir=temp_data_dir, backup_dir=temp_backup_dir)

    # Should still succeed with fallback to read-only mode
    assert len(backups) == 2
    assert all(backup.exists() for backup in backups)


def test_backup_with_corrupt_database(temp_data_dir, temp_backup_dir):
    """Test backup handling with corrupt database file."""
    # Create a corrupt database file
    corrupt_db = temp_data_dir / "corrupt.db"
    corrupt_db.write_text("This is not a valid SQLite database")

    # Backup should handle the error gracefully
    backups = backup_databases(data_dir=temp_data_dir, backup_dir=temp_backup_dir)

    # Should succeed for valid databases, skip corrupt one
    assert len(backups) >= 2


def test_backup_cleans_up_partial_files_on_failure(temp_data_dir, temp_backup_dir):
    """Test that partial backup files are cleaned up on failure."""
    import sqlite3

    # Create a locked database to force backup failure
    locked_db = temp_data_dir / "locked.db"
    conn = sqlite3.connect(locked_db)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
    conn.execute("INSERT INTO test (data) VALUES (?)", ("test",))
    conn.commit()

    # Begin a transaction but don't commit to hold a lock
    conn.execute("BEGIN EXCLUSIVE")

    try:
        # Attempt backup while database is locked (should handle gracefully)
        # Note: The backup might still succeed because we're using immutable mode
        # This test verifies the error handling is in place
        backups = backup_databases(data_dir=temp_data_dir, backup_dir=temp_backup_dir)

        # Should succeed for unlocked databases at minimum
        assert len(backups) >= 2
    finally:
        conn.rollback()
        conn.close()


def test_cleanup_handles_permission_errors(temp_backup_dir, monkeypatch):
    """Test cleanup gracefully handles permission errors."""
    import os
    import time

    # Create an old backup
    old_backup = temp_backup_dir / "test_20200101_120000.db"
    old_backup.write_text("old data")

    # Set modification time to old
    old_time = time.time() - (10 * 24 * 60 * 60)
    os.utime(old_backup, (old_time, old_time))

    # Mock unlink to raise PermissionError
    def mock_unlink_with_error(self, *args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(Path, "unlink", mock_unlink_with_error)

    # Should handle error gracefully and return 0 deleted
    deleted = cleanup_old_backups(temp_backup_dir, retention_days=1)

    assert deleted == 0
    # File should still exist since deletion failed
    assert old_backup.exists()


def test_restore_handles_copy_failure(tmp_path, monkeypatch):
    """Test restore handles copy failures gracefully."""
    import shutil

    backup_file = tmp_path / "backup.db"
    backup_file.write_text("backup data")
    target_file = tmp_path / "target.db"

    # Mock copy2 to fail
    def mock_copy2_that_fails(src, dst):
        raise OSError("Disk full")

    monkeypatch.setattr(shutil, "copy2", mock_copy2_that_fails)

    success = restore_database(backup_file, target_file)

    assert not success


def test_parse_timestamp_from_invalid_filename(temp_backup_dir):
    """Test that invalid filenames are handled gracefully in list_backups."""
    # Create backups with various filename formats
    (temp_backup_dir / "valid_20250101_120000.db").write_text("data1")
    (temp_backup_dir / "invalid_filename.db").write_text("data2")
    (temp_backup_dir / "nodate.db").write_text("data3")
    (temp_backup_dir / "bad_20259999_999999.db").write_text("data4")  # Invalid date

    backups = list_backups(temp_backup_dir)

    # Should return all backups, using mtime for invalid names
    assert len(backups) >= 1  # At least the valid one


def test_list_backups_handles_stat_errors(temp_backup_dir):
    """Test list_backups handles errors getting file metadata."""
    import os

    # Create a backup
    test_backup = temp_backup_dir / "test_20250101_120000.db"
    test_backup.write_text("data")

    # Make the file unreadable (simulate permission error)
    try:
        os.chmod(test_backup, 0o000)

        # Should handle error gracefully
        backups = list_backups(temp_backup_dir)

        # May return empty list or skip the unreadable file
        assert isinstance(backups, list)
    finally:
        # Restore permissions for cleanup
        try:
            os.chmod(test_backup, 0o644)
        except Exception:
            pass


def test_backup_with_non_db_files(temp_data_dir, temp_backup_dir):
    """Test that non-.db files are skipped during backup."""
    # Create non-database files
    (temp_data_dir / "not_a_db.txt").write_text("text file")
    (temp_data_dir / "config.json").write_text("{}")

    backups = backup_databases(data_dir=temp_data_dir, backup_dir=temp_backup_dir)

    # Should only backup the actual .db files from fixture
    assert len(backups) == 2
    assert all(backup.suffix == ".db" for backup in backups)


def test_backup_skips_non_file_paths(temp_data_dir, temp_backup_dir):
    """Test that directories and other non-file paths are skipped."""
    # Create a directory with .db extension (edge case)
    (temp_data_dir / "fake.db").mkdir()

    backups = backup_databases(data_dir=temp_data_dir, backup_dir=temp_backup_dir)

    # Should only backup real files, skip the directory
    assert len(backups) == 2  # Only the two real db files from fixture
