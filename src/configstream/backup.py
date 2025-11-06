"""
Database Backup Module
Automatically backs up SQLite databases with timestamp-based naming and retention policy.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

logger = logging.getLogger(__name__)


def backup_databases(
    data_dir: Path | str = Path("data"),
    backup_dir: Path | str | None = None,
    retention_days: int = 7,
) -> List[Path]:
    """
    Create timestamped backups of all SQLite databases in data directory.

    Args:
        data_dir: Directory containing database files
        backup_dir: Directory to store backups (defaults to data_dir/backups)
        retention_days: Number of days to keep old backups

    Returns:
        List of backup file paths created
    """
    data_dir = Path(data_dir)
    if backup_dir is None:
        backup_dir = data_dir / "backups"
    else:
        backup_dir = Path(backup_dir)

    # Create backup directory if it doesn't exist
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp for this backup run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Find all .db files in data directory
    db_files = list(data_dir.glob("*.db"))

    if not db_files:
        logger.warning("No database files found in %s", data_dir)
        return []

    backups_created = []

    # Backup each database
    for db_file in db_files:
        if not db_file.is_file():
            continue

        backup_filename = f"{db_file.stem}_{timestamp}.db"
        backup_path = backup_dir / backup_filename

        try:
            # Prefer immutable read to avoid writer interference (requires SQLite >= 3.22)
            src_uri = f"file:{db_file}?mode=ro&immutable=1"
            try:
                src_conn = sqlite3.connect(src_uri, uri=True, timeout=5.0)
            except sqlite3.OperationalError:
                # Fallback to read-only without immutable if unsupported
                src_conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True, timeout=5.0)

            with src_conn as src, sqlite3.connect(backup_path, timeout=5.0) as dst:
                # Try incremental backup with small pages to reduce lock time
                try:
                    src.backup(dst, pages=1000, progress=None)
                except TypeError:
                    # Older Python/SQLite without 'pages' kwarg
                    src.backup(dst)

            shutil.copystat(db_file, backup_path)

            backups_created.append(backup_path)
            logger.info(
                "Backed up %s -> %s (%.2f MB)",
                db_file.name,
                backup_filename,
                backup_path.stat().st_size / 1024 / 1024,
            )

        except Exception as e:
            # Clean up any partial file
            try:
                if backup_path.exists():
                    backup_path.unlink()
            except Exception:
                pass
            logger.error("Failed to backup %s: %s", db_file, e)

    # Cleanup old backups
    if retention_days > 0:
        cleaned = cleanup_old_backups(backup_dir, retention_days)
        if cleaned > 0:
            logger.info("Cleaned up %d old backup files", cleaned)

    logger.info("Backup complete: %d databases backed up", len(backups_created))
    return backups_created


def cleanup_old_backups(backup_dir: Path, retention_days: int) -> int:
    """
    Remove backup files older than retention_days.

    Args:
        backup_dir: Directory containing backups
        retention_days: Age threshold in days

    Returns:
        Number of files deleted
    """
    if not backup_dir.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted = 0

    for backup_file in backup_dir.glob("*.db"):
        try:
            # Get file modification time
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)

            if mtime < cutoff:
                file_size = backup_file.stat().st_size / 1024 / 1024
                backup_file.unlink()
                deleted += 1
                logger.debug(
                    "Deleted old backup: %s (%.2f MB, age: %d days)",
                    backup_file.name,
                    file_size,
                    (datetime.now() - mtime).days,
                )

        except Exception as e:
            logger.warning("Failed to delete old backup %s: %s", backup_file, e)

    return deleted


def restore_database(backup_file: Path, target_file: Path) -> bool:
    """
    Restore a database from backup.

    Args:
        backup_file: Path to backup file
        target_file: Path to restore to

    Returns:
        True if successful, False otherwise
    """
    if not backup_file.exists():
        logger.error("Backup file does not exist: %s", backup_file)
        return False

    try:
        # Create backup of current file if it exists
        if target_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore_backup = target_file.with_suffix(f".pre_restore_{timestamp}.db")
            shutil.copy2(target_file, pre_restore_backup)
            logger.info("Created pre-restore backup: %s", pre_restore_backup.name)

        # Restore from backup
        shutil.copy2(backup_file, target_file)
        logger.info("Restored %s from %s", target_file.name, backup_file.name)
        return True

    except Exception as e:
        logger.error("Failed to restore database: %s", e)
        return False


def _parse_timestamp_from_name(name: str) -> datetime | None:
    """Parse timestamp from backup filename."""
    # expect pattern: <stem>_YYYYMMDD_HHMMSS.db
    m = re.search(r"_(\d{8})_(\d{6})\.db$", name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    except ValueError:
        return None


def list_backups(backup_dir: Path | str = Path("data/backups")) -> List[dict]:
    """
    List all available backups with metadata.

    Args:
        backup_dir: Directory containing backups

    Returns:
        List of backup metadata dictionaries
    """
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return []

    backups = []

    for backup_file in sorted(backup_dir.glob("*.db"), key=lambda p: p.name, reverse=True):
        try:
            stat = backup_file.stat()
            created = _parse_timestamp_from_name(backup_file.name) or datetime.fromtimestamp(
                stat.st_mtime
            )
            backups.append(
                {
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size_mb": stat.st_size / 1024 / 1024,
                    "created": created,
                    "age_days": (datetime.now() - created).days,
                }
            )
        except Exception as e:
            logger.warning("Failed to get metadata for %s: %s", backup_file, e)

    return backups


def get_backup_statistics(backup_dir: Path | str = Path("data/backups")) -> dict:
    """
    Get statistics about backups.

    Args:
        backup_dir: Directory containing backups

    Returns:
        Dictionary with backup statistics
    """
    backups = list_backups(backup_dir)

    if not backups:
        return {
            "total_backups": 0,
            "total_size_mb": 0.0,
            "oldest_backup": None,
            "newest_backup": None,
        }

    return {
        "total_backups": len(backups),
        "total_size_mb": sum(b["size_mb"] for b in backups),
        "oldest_backup": backups[-1]["created"],
        "newest_backup": backups[0]["created"],
        "backups_by_database": _group_backups_by_database(backups),
    }


def _group_backups_by_database(backups: List[dict]) -> Dict[str, List[dict]]:
    """Group backups by database name."""
    grouped: Dict[str, List[dict]] = {}
    # Regex to remove timestamp suffix like _YYYYMMDD_HHMMSS
    timestamp_pattern = re.compile(r"_\d{8}_\d{6}$")

    for backup in backups:
        # Extract database name from filename (remove timestamp and .db extension)
        base_name = backup["filename"].removesuffix(".db")
        db_name = timestamp_pattern.sub("", base_name)

        if db_name not in grouped:
            grouped[db_name] = []
        grouped[db_name].append(backup)
    return grouped
