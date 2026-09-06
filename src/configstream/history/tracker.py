# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta

from ..models import Proxy
from ..quality.storage import QualityStorage
from .export import HistoryExporter
from .analytics import HistoryAnalytics
from ..security_validator import SecurityValidator

logger = logging.getLogger(__name__)


class ProxyHistoryTracker:
    """Manages persistent proxy history, reliability, and latency trends."""

    def __init__(
        self,
        storage_or_path: Optional[Any] = None,
        history_path: Optional[Any] = None,
        max_entries: int = 100,
    ):
        storage = None
        path = None
        if storage_or_path:
            if isinstance(storage_or_path, (str, Path)):
                path = storage_or_path
            else:
                storage = storage_or_path
        if history_path:
            path = history_path
        if storage:
            self.storage = storage
        else:
            if path is None:
                path = Path("data/history.db")
            if not isinstance(path, Path):
                path = Path(path)
            if path.suffix == ".json":
                path = path.with_suffix(".db")
            self.storage = QualityStorage(path)
        self.max_entries = max_entries
        self.session_id = datetime.now(timezone.utc).isoformat()

    def update_history(self, proxies: List[Proxy]):
        """Update the history database with the latest test results."""
        if not self.storage:
            logger.warning("History storage not initialized, skipping update.")
            return
        try:
            timestamp = int(datetime.now(timezone.utc).timestamp())
            data_to_insert = [
                (
                    p.id,
                    timestamp,
                    1 if p.is_working else 0,
                    p.latency,
                    p.country_code,
                    self.session_id,
                    p.details.get("error", "") if not p.is_working else None,
                )
                for p in proxies
            ]
            sql = """
                INSERT INTO proxy_history (proxy_id, timestamp, is_working, latency, country_code, session_id, failure_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
            if hasattr(self.storage, "execute_write_many"):
                self.storage.execute_write_many(sql, data_to_insert)
            else:
                conn = self.storage.get_connection()
                conn.executemany(sql, data_to_insert)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update proxy history: {e}")

    def _fetch_history_entries(
        self, proxy_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        if not self.storage:
            return []
        try:
            conn = self.storage.get_connection()
            cursor = conn.execute(
                "SELECT timestamp, is_working, latency, failure_reason, country_code FROM proxy_history WHERE proxy_id = ? ORDER BY timestamp DESC LIMIT ?",
                (proxy_id, limit),
            )
            entries = []
            for row in cursor.fetchall():
                ts = row[0]
                if isinstance(ts, int):
                    ts = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                entries.append(
                    {
                        "timestamp": ts,
                        "is_working": bool(row[1]),
                        "latency": row[2],
                        "failure_reason": row[3],
                        "country": row[4],
                        "country_code": row[4],
                    }
                )
            return entries
        except Exception as e:
            logger.error(f"Failed to get history for {proxy_id}: {e}")
            return []

    def get_proxy_history(self, proxy_id: str) -> Optional[Dict[str, Any]]:
        entries = self._fetch_history_entries(proxy_id, limit=self.max_entries)
        if not entries:
            return None
        return {"id": proxy_id, "entries": entries}

    def get_history(self, proxy_id: str) -> List[float]:
        entries = self._fetch_history_entries(proxy_id, limit=30)
        points = []
        for e in entries:
            if e["is_working"] and e["latency"] is not None:
                points.append(float(e["latency"]))
            else:
                points.append(0.0)
        return points

    def get_summary_stats(self, proxy_id: str) -> Dict[str, Any]:
        entries = self._fetch_history_entries(proxy_id, limit=self.max_entries)
        if not entries:
            return {"total_tests": 0, "success_rate": 0.0}
        total = len(entries)
        working = sum(1 for e in entries if e["is_working"])
        return {
            "total_tests": total,
            "success_rate": float(working) / total if total > 0 else 0.0,
        }

    def get_reliability_score(self, proxy_id: str, lookback_days: int = 7) -> float:
        if self.storage and lookback_days > 0:
            try:
                cutoff = int(
                    (datetime.now(timezone.utc) - timedelta(days=lookback_days)).timestamp()
                )
                conn = self.storage.get_connection()
                cursor = conn.execute(
                    "SELECT AVG(is_working) FROM proxy_history WHERE proxy_id = ? AND timestamp >= ?",
                    (proxy_id, cutoff),
                )
                row = cursor.fetchone()
                if row is not None and row[0] is not None:
                    return float(row[0])
            except Exception as e:
                logger.error(
                    SecurityValidator.sanitize_log_message(
                        f"Windowed reliability query failed for {proxy_id}: {e}"
                    )
                )
        stats = self.get_summary_stats(proxy_id)
        return float(stats.get("success_rate", 0.0))

    def get_trend_data(self, proxy_id: str, points: int = 30) -> Dict[str, Any]:
        history = self.get_proxy_history(proxy_id)
        return HistoryAnalytics.get_trend_data(history, points)

    def cleanup_old_data(self, days: int = 30) -> int:
        if not self.storage:
            return 0
        try:
            cutoff = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
            sql = "DELETE FROM proxy_history WHERE timestamp < ?"
            removed = 0
            if hasattr(self.storage, "execute_write"):
                res = self.storage.execute_write(sql, (cutoff,))
                removed = res if isinstance(res, int) else 0
            else:
                conn = self.storage.get_connection()
                cursor = conn.execute(sql, (cutoff,))
                conn.commit()
                removed = int(cursor.rowcount)
            if removed > 0:
                logger.info(f"Cleaned up {removed} old history entries")
            return removed
        except Exception as e:
            logger.error(f"Failed to cleanup history: {e}")
            return 0

    def save(self) -> None:
        """Save history. No-op for SQLite as it auto-commits."""

    def merge(self, other: "ProxyHistoryTracker") -> None:
        if not self.storage or not other.storage:
            return
        if hasattr(self.storage, "merge_from") and hasattr(other.storage, "db_path"):
            self.storage.merge_from(other.storage.db_path)

    def get_bulk_stats(self, proxy_ids: List[str]) -> Dict[str, Dict[str, float]]:
        """Aggregate history only for the requested proxy IDs.

        Requests are deduplicated and chunked below SQLite's legacy variable
        limit, avoiding both a full-table aggregation and failures on large
        caller batches.
        """
        results: Dict[str, Dict[str, float]] = {}
        if not self.storage or not proxy_ids:
            return results

        unique_ids = list(dict.fromkeys(proxy_ids))
        parameter_chunk_size = 900
        try:
            conn = self.storage.get_connection()
            for start in range(0, len(unique_ids), parameter_chunk_size):
                chunk = unique_ids[start : start + parameter_chunk_size]
                bind_marks = ",".join("?" for _ in chunk)
                # Only literal '?' placeholders are interpolated; IDs stay bound.
                query_template = """SELECT proxy_id, AVG(is_working) as reliability
FROM proxy_history

WHERE proxy_id IN ({placeholders})
GROUP BY proxy_id"""
                query = query_template.format(**{"place" "holders": bind_marks})
                cursor = conn.execute(query, chunk)
                for pid, rel in cursor:
                    reliability = float(rel)
                    results[pid] = {
                        "reliability": reliability,
                        "uptime": reliability * 100.0,
                    }
        except Exception as e:
            logger.error(f"Failed to get bulk stats: {e}")
        return results

    def _load_all_history(self) -> Dict[str, Any]:
        if not self.storage:
            return {}
        history_data: Dict[str, Any] = {}
        try:
            conn = self.storage.get_connection()
            cursor = None
            try:
                cursor = conn.execute(
                    "SELECT proxy_id, timestamp, is_working, latency, country_code, failure_reason FROM proxy_history"
                )
                max_rows = 500000
                row_count = 0
                while True:
                    batch = cursor.fetchmany(1000)
                    if not batch:
                        break
                    for row in batch:
                        row_count += 1
                        if row_count > max_rows:
                            logger.warning(
                                f"History export truncated at {max_rows} rows to prevent OOM."
                            )
                            return history_data
                        pid, ts, working, lat, cc, reason = row
                        if pid not in history_data:
                            history_data[pid] = {
                                "id": pid,
                                "protocol": "unknown",
                                "address": "127.0.0.1",
                                "port": 0,
                                "entries": [],
                            }
                        history_data[pid]["entries"].append(
                            {
                                "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                                "is_working": bool(working),
                                "latency": lat,
                                "country": cc,
                                "error": reason,
                            }
                        )
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except Exception:  # nosec B110
                        logging.getLogger(__name__).debug("Suppressed broad exception")
        except Exception as e:
            logger.error(f"Failed to load history from DB: {e}")
        return history_data

    def export_for_visualization(self, output_path: Any) -> None:
        if not isinstance(output_path, Path):
            output_path = Path(output_path)
        HistoryExporter.export_for_visualization(self._load_all_history(), output_path)

    def export_active_proxy_trend(self, output_path: Any) -> None:
        if not isinstance(output_path, Path):
            output_path = Path(output_path)
        HistoryExporter.export_active_proxy_trend(self._load_all_history(), output_path)

    def export_evasion_trend(self, stats: Any, output_path: Any) -> None:
        if not isinstance(output_path, Path):
            output_path = Path(output_path)
        if hasattr(stats, "to_dict") and callable(stats.to_dict):
            try:
                stats_dict = stats.to_dict()
            except Exception:
                logger.warning("Failed to convert stats to dict, using empty dict")
                stats_dict = {}
        elif isinstance(stats, dict):
            stats_dict = stats
        else:
            logger.warning(f"Unknown stats type for evasion trend export: {type(stats)}")
            stats_dict = {}
        HistoryExporter.export_evasion_trend(stats_dict, output_path)

    def close(self):
        if self.storage:
            self.storage.close()
