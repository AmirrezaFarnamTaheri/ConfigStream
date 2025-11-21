import pytest
from unittest.mock import patch, MagicMock
from configstream.backup import (
    backup_databases,
    restore_database,
    list_backups,
    cleanup_old_backups,
)
from pathlib import Path
import shutil
import sqlite3
from datetime import datetime, timedelta


@pytest.fixture
def setup_backup_env(tmp_path):
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backups"
    data_dir.mkdir()
    backup_dir.mkdir()

    # Create a dummy db
    db_file = data_dir / "test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE test (id INTEGER)")
    conn.execute("INSERT INTO test VALUES (1)")
    conn.commit()
    conn.close()

    return data_dir, backup_dir, db_file


def test_backup_databases(setup_backup_env):
    data_dir, backup_dir, db_file = setup_backup_env

    backups = backup_databases(data_dir, backup_dir)

    assert len(backups) == 1
    assert backups[0].exists()
    assert backups[0].stat().st_size > 0
    assert "test" in backups[0].name


def test_cleanup_old_backups(setup_backup_env):
    data_dir, backup_dir, _ = setup_backup_env

    # Create an old backup
    old_backup = backup_dir / "old_20200101_000000.db"
    old_backup.touch()
    # Set mtime to way back
    # old_time removed
    # os_utime_mock removed

    # Since we can't easily mock os.stat time in integration without complex patching,
    # we rely on the fact that cleanup checks file mtime.
    # Let's use explicit patching of glob results or datetime

    with patch("configstream.backup.datetime") as mock_dt:
        # Mock current time to be far in future relative to file mtime
        mock_dt.now.return_value = datetime.now() + timedelta(days=100)
        mock_dt.fromtimestamp.side_effect = datetime.fromtimestamp

        deleted = cleanup_old_backups(backup_dir, retention_days=7)
        assert deleted == 1
        assert not old_backup.exists()


def test_restore_database(setup_backup_env):
    data_dir, backup_dir, db_file = setup_backup_env

    # Backup first
    backups = backup_databases(data_dir, backup_dir)
    backup_file = backups[0]

    # Modify original db
    conn = sqlite3.connect(db_file)
    conn.execute("INSERT INTO test VALUES (2)")
    conn.commit()
    conn.close()

    # Restore
    success = restore_database(backup_file, db_file)
    assert success

    # Verify content
    conn = sqlite3.connect(db_file)
    rows = conn.execute("SELECT * FROM test").fetchall()
    conn.close()
    assert len(rows) == 1  # Should be back to 1 row


def test_list_backups(setup_backup_env):
    data_dir, backup_dir, _ = setup_backup_env
    backup_databases(data_dir, backup_dir)

    backups = list_backups(backup_dir)
    assert len(backups) == 1
    assert "created" in backups[0]
    assert "size_mb" in backups[0]
