# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Database Backup Module
Automatically backs up SQLite databases with timestamp-based naming and retention policy.
"""

from __future__ import annotations

import gzip
import logging
import os
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

from .security_validator import safe_log_text

logger = logging.getLogger(__name__)

MAX_RESTORE_DATABASE_BYTES = 2 * 1024 * 1024 * 1024
RESTORE_COPY_CHUNK_BYTES = 1024 * 1024


def backup_databases(
    data_dir: Path | str = Path("data"),
    backup_dir: Path | str | None = None,
    retention_days: int = 7,
) -> List[Path]:
    """Create crash-consistent timestamped backups of SQLite databases."""
    data_dir = Path(data_dir)
    backup_dir = data_dir / "backups" if backup_dir is None else Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_files = list(data_dir.glob("*.db"))
    if not db_files:
        logger.warning("No database files found in %s", data_dir)
        return []

    backups_created: List[Path] = []
    for db_file in db_files:
        if not db_file.is_file():
            continue

        safe_stem = db_file.stem.replace("..", "_").replace("/", "_").replace("\\", "_")
        backup_path_temp = backup_dir / f"{safe_stem}_{timestamp}.db"
        backup_path_final = backup_dir / f"{safe_stem}_{timestamp}.db.gz"
        compressed_temp = backup_dir / f".{backup_path_final.name}.{os.getpid()}.tmp"

        try:
            backup_path_temp.resolve().relative_to(backup_dir.resolve())
            backup_path_final.resolve().relative_to(backup_dir.resolve())
            compressed_temp.resolve().relative_to(backup_dir.resolve())
        except ValueError:
            logger.error("Skipping backup: path traversal detected for %s", db_file)
            continue

        try:
            # Participate in SQLite's normal read/locking protocol. ``immutable=1``
            # must not be used against a live WAL database because it can ignore
            # committed pages that have not yet been checkpointed into the main file.
            src_conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True, timeout=5.0)
            src_conn.execute("PRAGMA query_only=ON")
            dst_conn = None
            try:
                dst_conn = sqlite3.connect(backup_path_temp, timeout=5.0)
                try:
                    src_conn.backup(dst_conn, pages=1000, progress=None)
                except TypeError:
                    src_conn.backup(dst_conn)
            finally:
                if dst_conn is not None:
                    dst_conn.close()
                src_conn.close()

            # Publish the compressed backup atomically. A crash during gzip creation
            # must never leave a truncated file under the final backup name.
            with (
                backup_path_temp.open("rb") as f_in,
                compressed_temp.open("wb") as raw_out,
            ):
                with gzip.GzipFile(fileobj=raw_out, mode="wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
                raw_out.flush()
                os.fsync(raw_out.fileno())
            os.replace(compressed_temp, backup_path_final)
            backup_path_temp.unlink(missing_ok=True)

            backups_created.append(backup_path_final)
            size_mb = backup_path_final.stat().st_size / 1024 / 1024
            logger.info(
                "Backed up %s -> %s (%.2f MB)",
                db_file.name,
                backup_path_final.name,
                size_mb,
            )
        except Exception as exc:
            for partial in (backup_path_temp, compressed_temp):
                try:
                    partial.unlink(missing_ok=True)
                except OSError as cleanup_exc:
                    logger.debug(
                        "Failed to remove partial backup %s: %s",
                        partial.name,
                        safe_log_text(cleanup_exc),
                    )
            logger.error("Failed to backup %s: %s", db_file, safe_log_text(exc))

    if retention_days > 0:
        cleaned = cleanup_old_backups(backup_dir, retention_days)
        if cleaned > 0:
            logger.info("Cleaned up %d old backup files", cleaned)

    logger.info("Backup complete: %d databases backed up", len(backups_created))
    return backups_created


def cleanup_old_backups(backup_dir: Path, retention_days: int) -> int:
    """Keep recent backups, then thin older backups to one per day."""
    if not backup_dir.exists():
        return 0

    now = datetime.now()
    cutoff_retention = now - timedelta(days=retention_days)
    cutoff_absolute = now - timedelta(days=30)
    deleted = 0
    backups = list(backup_dir.glob("*.db")) + list(backup_dir.glob("*.db.gz"))
    by_db_date: Dict[Tuple[str, str], List[Tuple[datetime, Path]]] = {}

    for backup_file in backups:
        try:
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            if mtime < cutoff_absolute:
                backup_file.unlink()
                deleted += 1
                continue
            if mtime >= cutoff_retention:
                continue

            stem = backup_file.name
            if stem.endswith(".db.gz"):
                stem = stem[:-6]
            elif stem.endswith(".db"):
                stem = stem[:-3]
            parts = stem.split("_")
            db_name = (
                "_".join(parts[:-2])
                if len(parts) >= 3 and len(parts[-1]) == 6 and len(parts[-2]) == 8
                else "unknown"
            )
            key = (db_name, mtime.strftime("%Y-%m-%d"))
            by_db_date.setdefault(key, []).append((mtime, backup_file))
        except Exception as exc:
            logger.warning(
                "Failed to process backup %s: %s", backup_file, safe_log_text(exc)
            )

    for file_list in by_db_date.values():
        file_list.sort(key=lambda item: item[0], reverse=True)
        for _, fpath in file_list[1:]:
            try:
                fpath.unlink()
                deleted += 1
            except Exception as cleanup_exc:
                logger.debug(
                    "Failed to delete old backup %s: %s",
                    fpath.name,
                    safe_log_text(cleanup_exc),
                )

    if deleted > 0:
        logger.info("Cleaned up %d old backup files (smart retention)", deleted)
    return deleted


def _sqlite_backup(source: Path, destination: Path) -> None:
    """Copy a database through SQLite's locking protocol."""
    source_conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=5.0)
    source_conn.execute("PRAGMA query_only=ON")
    destination_conn: sqlite3.Connection | None = None
    try:
        destination_conn = sqlite3.connect(destination, timeout=5.0)
        try:
            source_conn.backup(destination_conn, pages=1000, progress=None)
        except TypeError:
            source_conn.backup(destination_conn)
    finally:
        if destination_conn is not None:
            destination_conn.close()
        source_conn.close()


def restore_database(backup_file: Path, target_file: Path) -> bool:
    """Restore a validated SQLite backup without replacing a live database inode.

    The candidate is first decompressed into a private temporary database and
    validated with ``PRAGMA quick_check``. Publication then uses SQLite's online
    backup API so WAL/SHM state and active connections participate in SQLite's
    own locking protocol. This avoids swapping the main database file underneath
    live connections, which can otherwise mix database generations.
    """
    backup_file = Path(backup_file)
    target_file = Path(target_file)
    temp_path: Path | None = None

    try:
        if not backup_file.exists():
            logger.error("Backup file does not exist: %s", backup_file)
            return False

        target_file.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{target_file.name}.restore-", dir=target_file.parent
        )
        os.close(fd)
        temp_path = Path(temp_name)

        opener = gzip.open if backup_file.name.endswith(".gz") else open
        with opener(backup_file, "rb") as f_in, temp_path.open("wb") as f_out:
            restored_bytes = 0
            while chunk := f_in.read(RESTORE_COPY_CHUNK_BYTES):
                restored_bytes += len(chunk)
                if restored_bytes > MAX_RESTORE_DATABASE_BYTES:
                    raise ValueError("restored database exceeds the safety limit")
                f_out.write(chunk)
            if restored_bytes == 0:
                raise ValueError("restored database is empty")
            f_out.flush()
            os.fsync(f_out.fileno())

        check_conn = sqlite3.connect(f"file:{temp_path}?mode=ro", uri=True, timeout=5.0)
        try:
            row = check_conn.execute("PRAGMA quick_check").fetchone()
        finally:
            check_conn.close()
        if row is None or str(row[0]).lower() != "ok":
            raise sqlite3.DatabaseError("restored backup failed PRAGMA quick_check")

        if target_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore_backup = target_file.with_suffix(f".pre_restore_{timestamp}.db")
            _sqlite_backup(target_file, pre_restore_backup)
            logger.info("Created pre-restore backup: %s", pre_restore_backup.name)

        # Never os.replace() the main database while another connection may own
        # a WAL generation. The SQLite backup API writes through the destination
        # database's normal pager/locking protocol and keeps existing connections
        # attached to the same database file generation.
        _sqlite_backup(temp_path, target_file)
        logger.info("Restored %s from %s", target_file.name, backup_file.name)
        return True
    except Exception as exc:
        logger.error("Failed to restore database: %s", safe_log_text(exc))
        return False
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError as cleanup_exc:
                logger.debug(
                    "Failed to remove restore temp file %s: %s",
                    temp_path.name,
                    safe_log_text(cleanup_exc),
                )


def _parse_timestamp_from_name(name: str) -> datetime | None:
    """Parse timestamp from backup filename."""
    clean_name = name[:-3] if name.endswith(".gz") else name
    clean_name = clean_name[:-3] if clean_name.endswith(".db") else clean_name
    match = re.search(r"_(\d{8})_(\d{6})$", clean_name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S")
    except ValueError:
        return None


def list_backups(backup_dir: Path | str = Path("data/backups")) -> List[dict]:
    """List all available backups with metadata, newest first."""
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return []

    items: List[dict] = []
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
        except Exception as exc:
            logger.warning(
                "Failed to get metadata for %s: %s", backup_file, safe_log_text(exc)
            )
    return sorted(items, key=lambda backup: backup["created"], reverse=True)


def get_backup_statistics(backup_dir: Path | str = Path("data/backups")) -> dict:
    """Get statistics about backups."""
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
        "total_size_mb": sum(backup["size_mb"] for backup in backups),
        "oldest_backup": backups[-1]["created"],
        "newest_backup": backups[0]["created"],
        "backups_by_database": _group_backups_by_database(backups),
    }


def _group_backups_by_database(backups: List[dict]) -> Dict[str, List[dict]]:
    """Group backups by database name."""
    grouped: Dict[str, List[dict]] = {}
    timestamp_pattern = re.compile(r"_\d{8}_\d{6}$")
    for backup in backups:
        fname = backup["filename"]
        if fname.endswith(".db.gz"):
            base_name = fname[:-6]
        elif fname.endswith(".db"):
            base_name = fname[:-3]
        else:
            base_name = fname
        db_name = timestamp_pattern.sub("", base_name)
        grouped.setdefault(db_name, []).append(backup)
    return grouped
