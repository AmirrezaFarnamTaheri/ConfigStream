# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Database Backup Module
Automatically backs up SQLite databases with timestamp-based naming and retention policy.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
import logging
import gzip
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

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
        logger.warning(f"No database files found in {data_dir}")
        return []

    backups_created = []

    # Backup each database
    for db_file in db_files:
        if not db_file.is_file():
            continue

        # Sanitize filename to prevent path traversal
        safe_stem = db_file.stem.replace("..", "_").replace("/", "_").replace("\\", "_")
        # Temporary uncompressed name for backup processing
        backup_filename_temp = f"{safe_stem}_{timestamp}.db"
        backup_path_temp = backup_dir / backup_filename_temp

        # Final compressed name
        backup_filename_final = f"{safe_stem}_{timestamp}.db.gz"
        backup_path_final = backup_dir / backup_filename_final

        # Additional safety check: ensure resolved path is within backup directory
        try:
            backup_path_temp.resolve().relative_to(backup_dir.resolve())
        except ValueError:
            logger.error(f"Skipping backup: path traversal detected for {db_file}")
            continue

        try:
            # Prefer immutable read to avoid writer interference (requires SQLite >= 3.22)
            src_uri = f"file:{db_file}?mode=ro&immutable=1"
            try:
                src_conn = sqlite3.connect(src_uri, uri=True, timeout=5.0)
            except sqlite3.OperationalError:
                # Fallback to read-only without immutable if unsupported
                src_conn = sqlite3.connect(
                    f"file:{db_file}?mode=ro", uri=True, timeout=5.0
                )

            # Perform backup to temp file
            dst_conn = None
            try:
                dst_conn = sqlite3.connect(backup_path_temp, timeout=5.0)
                # Try incremental backup with small pages to reduce lock time
                try:
                    src_conn.backup(dst_conn, pages=1000, progress=None)
                except TypeError:
                    # Older Python/SQLite without 'pages' kwarg
                    src_conn.backup(dst_conn)
            finally:
                if dst_conn is not None:
                    dst_conn.close()
                src_conn.close()

            # Compress the backup using gzip
            with (
                open(backup_path_temp, "rb") as f_in,
                gzip.open(backup_path_final, "wb") as f_out,
            ):
                shutil.copyfileobj(f_in, f_out)

            # Remove uncompressed temp file
            if backup_path_temp.exists():
                backup_path_temp.unlink()

            backups_created.append(backup_path_final)

            size_mb = backup_path_final.stat().st_size / 1024 / 1024
            logger.info(
                f"Backed up {db_file.name} -> {backup_path_final.name} ({size_mb:.2f} MB)"
            )

        except Exception as e:
            # Clean up any partial files
            try:
                if backup_path_temp.exists():
                    backup_path_temp.unlink()
                if backup_path_final.exists():
                    backup_path_final.unlink()
            except Exception:
                pass
            logger.error(f"Failed to backup {db_file}: {e}")

    # Cleanup old backups
    if retention_days > 0:
        cleaned = cleanup_old_backups(backup_dir, retention_days)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old backup files")

    logger.info(f"Backup complete: {len(backups_created)} databases backed up")
    return backups_created


def cleanup_old_backups(backup_dir: Path, retention_days: int) -> int:
    """
    Smart cleanup: Keep recent backups, and thinning for older ones.
    Policy:
    - Keep all backups from last `retention_days` (e.g., 7 days).
    - For older than `retention_days`, keep 1 per day (daily snapshot).
    - Remove backups older than 30 days entirely.
    """
    if not backup_dir.exists():
        return 0

    now = datetime.now()
    cutoff_retention = now - timedelta(days=retention_days)
    cutoff_absolute = now - timedelta(days=30)  # Absolute max age

    deleted = 0

    # Gather all backups (.db and .db.gz)
    backups = list(backup_dir.glob("*.db")) + list(backup_dir.glob("*.db.gz"))

    # Group by (database_name, date_string)
    by_db_date: Dict[Tuple[str, str], List[Tuple[datetime, Path]]] = {}

    for backup_file in backups:
        try:
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)

            # Absolute cutoff
            if mtime < cutoff_absolute:
                backup_file.unlink()
                deleted += 1
                continue

            # If within recent retention window, keep
            if mtime >= cutoff_retention:
                continue

            # Identify DB name (remove timestamp suffix and extension)
            # Filename format: name_YYYYMMDD_HHMMSS.db[.gz]
            # Remove extensions
            stem = backup_file.name
            if stem.endswith(".db.gz"):
                stem = stem[:-6]
            elif stem.endswith(".db"):
                stem = stem[:-3]

            # Expect parts separated by underscores, last two are date and time
            parts = stem.split("_")
            if len(parts) >= 3 and len(parts[-1]) == 6 and len(parts[-2]) == 8:
                db_name = "_".join(parts[:-2])
            else:
                # Fallback if naming convention doesn't match
                db_name = "unknown"

            date_key = mtime.strftime("%Y-%m-%d")
            key = (db_name, date_key)
            if key not in by_db_date:
                by_db_date[key] = []
            by_db_date[key].append((mtime, backup_file))

        except Exception as e:
            logger.warning(f"Failed to process backup {backup_file}: {e}")

    # Process thinning groups (keep only 1 per day per DB)
    for key, file_list in by_db_date.items():
        # Sort by mtime descending (newest first)
        file_list.sort(key=lambda x: x[0], reverse=True)

        # Keep index 0 (newest for that day), delete others
        for _, fpath in file_list[1:]:
            try:
                fpath.unlink()
                deleted += 1
            except Exception:
                pass

    if deleted > 0:
        logger.info(f"Cleaned up {deleted} old backup files (smart retention)")

    return deleted


def restore_database(backup_file: Path, target_file: Path) -> bool:
    """
    Restore a database from backup.

    Args:
        backup_file: Path to backup file (.db or .db.gz)
        target_file: Path to restore to (.db)

    Returns:
        True if successful, False otherwise
    """
    if not backup_file.exists():
        logger.error(f"Backup file does not exist: {backup_file}")
        return False

    try:
        # Create pre-restore backup of current target if it exists
        if target_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Preserve current state before overwriting
            pre_restore_backup = target_file.with_suffix(f".pre_restore_{timestamp}.db")
            shutil.copy2(target_file, pre_restore_backup)
            logger.info(f"Created pre-restore backup: {pre_restore_backup.name}")

        # Restore from backup
        if backup_file.name.endswith(".gz"):
            # Decompress
            with (
                gzip.open(backup_file, "rb") as f_in,
                open(target_file, "wb") as f_out,
            ):
                shutil.copyfileobj(f_in, f_out)
        else:
            # Copy plain file
            shutil.copy2(backup_file, target_file)

        logger.info(f"Restored {target_file.name} from {backup_file.name}")
        return True

    except Exception as e:
        logger.error(f"Failed to restore database: {e}")
        return False


def _parse_timestamp_from_name(name: str) -> datetime | None:
    """Parse timestamp from backup filename."""
    # Pattern: <stem>_YYYYMMDD_HHMMSS.db[.gz]
    # Remove extensions first
    clean_name = name
    if clean_name.endswith(".gz"):
        clean_name = clean_name[:-3]
    if clean_name.endswith(".db"):
        clean_name = clean_name[:-3]

    m = re.search(r"_(\d{8})_(\d{6})$", clean_name)
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

    items: List[dict] = []

    # Match .db and .db.gz
    for backup_file in list(backup_dir.glob("*.db")) + list(backup_dir.glob("*.db.gz")):
        try:
            stat = backup_file.stat()
            created = _parse_timestamp_from_name(
                backup_file.name
            ) or datetime.fromtimestamp(stat.st_mtime)
            items.append(
                {
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size_mb": stat.st_size / 1024 / 1024,
                    "created": created,
                    "age_days": (datetime.now() - created).days,
                    "compressed": backup_file.name.endswith(".gz"),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to get metadata for {backup_file}: {e}")

    # Always return newest-first by actual creation time
    backups = sorted(items, key=lambda b: b["created"], reverse=True)
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
        # Extract database name from filename (remove extensions first)
        fname = backup["filename"]
        if fname.endswith(".db.gz"):
            base_name = fname[:-6]
        elif fname.endswith(".db"):
            base_name = fname[:-3]
        else:
            base_name = fname

        db_name = timestamp_pattern.sub("", base_name)

        if db_name not in grouped:
            grouped[db_name] = []
        grouped[db_name].append(backup)
    return grouped
