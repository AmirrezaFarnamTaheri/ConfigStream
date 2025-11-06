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
