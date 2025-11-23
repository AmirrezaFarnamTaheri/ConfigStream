import pytest
from configstream.backup import backup_databases, cleanup_old_backups
from pathlib import Path
import sqlite3
import time


def test_backup_manager(tmp_path):
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backups"
    data_dir.mkdir()

    # Create dummy file
    db_file = data_dir / "test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE t (a INT)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()

    backups = backup_databases(data_dir=str(data_dir), backup_dir=str(backup_dir))

    assert len(backups) == 1
    assert backups[0].exists()

    # Cleanup
    # Trick timestamp
    # We can't easily mock file stats without patching os.stat
    # But we can verify it doesn't delete fresh files
    deleted = cleanup_old_backups(backup_dir, retention_days=1)
    assert deleted == 0
    assert backups[0].exists()
