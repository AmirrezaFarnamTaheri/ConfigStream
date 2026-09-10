# SPDX-License-Identifier: AGPL-3.0-or-later
import gzip
import sqlite3

from configstream.backup import backup_databases, cleanup_old_backups, restore_database


def test_backup_manager(tmp_path):
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backups"
    data_dir.mkdir()

    db_file = data_dir / "test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE t (a INT)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()

    backups = backup_databases(data_dir=str(data_dir), backup_dir=str(backup_dir))

    assert len(backups) == 1
    assert backups[0].exists()

    deleted = cleanup_old_backups(backup_dir, retention_days=1)
    assert deleted == 0
    assert backups[0].exists()


def test_backup_includes_committed_wal_state(tmp_path):
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backups"
    data_dir.mkdir()
    db_file = data_dir / "wal.db"

    writer = sqlite3.connect(db_file)
    assert writer.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
    writer.execute("PRAGMA wal_autocheckpoint=0")
    writer.execute("CREATE TABLE records(value TEXT)")
    writer.commit()
    writer.execute("INSERT INTO records VALUES ('committed-in-wal')")
    writer.commit()
    assert (data_dir / "wal.db-wal").exists()

    backups = backup_databases(data_dir=data_dir, backup_dir=backup_dir)
    assert len(backups) == 1

    restored_copy = tmp_path / "backup-copy.db"
    with gzip.open(backups[0], "rb") as source:
        restored_copy.write_bytes(source.read())
    with sqlite3.connect(restored_copy) as check:
        assert (
            check.execute("SELECT value FROM records").fetchone()[0]
            == "committed-in-wal"
        )
    writer.close()


def test_restore_invalid_backup_preserves_existing_database(tmp_path):
    target = tmp_path / "target.db"
    with sqlite3.connect(target) as conn:
        conn.execute("CREATE TABLE records(value TEXT)")
        conn.execute("INSERT INTO records VALUES ('original')")
        conn.commit()

    invalid = tmp_path / "invalid.db"
    invalid.write_bytes(b"not a sqlite database")

    assert restore_database(invalid, target) is False
    with sqlite3.connect(target) as conn:
        assert conn.execute("SELECT value FROM records").fetchone()[0] == "original"


def test_restore_refuses_active_wal_generation(tmp_path):
    target = tmp_path / "target.db"
    writer = sqlite3.connect(target)
    assert writer.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
    writer.execute("PRAGMA wal_autocheckpoint=0")
    writer.execute("CREATE TABLE records(value TEXT)")
    writer.execute("INSERT INTO records VALUES ('live')")
    writer.commit()
    assert (tmp_path / "target.db-wal").exists()

    backup = tmp_path / "backup.db"
    with sqlite3.connect(backup) as conn:
        conn.execute("CREATE TABLE records(value TEXT)")
        conn.execute("INSERT INTO records VALUES ('backup')")
        conn.commit()

    assert restore_database(backup, target) is False
    assert writer.execute("SELECT value FROM records").fetchone()[0] == "live"
    writer.close()
