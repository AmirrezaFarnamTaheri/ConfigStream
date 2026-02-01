# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta

from ..models import Proxy
from ..quality.storage import QualityStorage
from .export import HistoryExporter
from .analytics import HistoryAnalytics

logger = logging.getLogger(__name__)


class ProxyHistoryTracker:
    """
    Manages the persistent history of proxies, including:
    - Availability over time
    - Latency trends
    - Reliability scoring
    """

    def __init__(
        self,
        storage_or_path: Optional[Any] = None,
        history_path: Optional[Any] = None,
        max_entries: int = 100,
    ):
        # Handle positional arg which could be storage or path
        storage = None
        path = None

        if storage_or_path:
            # Check if it looks like a path (str or Path)
            from pathlib import Path

            if isinstance(storage_or_path, (str, Path)):
                path = storage_or_path
            else:
                # Assume it is QualityStorage
                storage = storage_or_path

        # history_path arg overrides positional path
        if history_path:
            path = history_path

        if storage:
            self.storage = storage
        else:
            from pathlib import Path

            if path is None:
                path = Path("data/history.db")

            if not isinstance(path, Path):
                path = Path(path)

            if path.suffix == ".json":
                path = path.with_suffix(".db")

            self.storage = QualityStorage(path)

        self.max_entries = max_entries
        self.session_id = datetime.now(timezone.utc).isoformat()

    def record_test_result(self, proxy: Proxy) -> None:
        """Record a single test result (compatibility alias)."""
        self.update_history([proxy])

    def update_history(self, proxies: List[Proxy]):
        """
        Updates the history database with the latest test results.
        Uses serialized write access to prevent database locks.
        """
        if not self.storage:
            logger.warning("History storage not initialized, skipping update.")
            return

        try:
            timestamp = int(datetime.now(timezone.utc).timestamp())

            data_to_insert = []
            for p in proxies:
                data_to_insert.append(
                    (
                        p.id,
                        timestamp,
                        1 if p.is_working else 0,
                        p.latency,
                        p.country_code,
                        self.session_id,
                        p.details.get("error", "") if not p.is_working else None,
                    )
                )

            sql = """
                INSERT INTO proxy_history (proxy_id, timestamp, is_working, latency, country_code, session_id, failure_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """

            # Use thread-safe write method if available
            if hasattr(self.storage, "execute_write_many"):
                self.storage.execute_write_many(sql, data_to_insert)
            else:
                # Fallback for legacy/mock storage
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
        """Get history in legacy dict format {entries: [...]}."""
        entries = self._fetch_history_entries(proxy_id, limit=self.max_entries)
        if not entries:
            return None
        return {"id": proxy_id, "entries": entries}

    def get_history(self, proxy_id: str) -> List[float]:
        """Get sparkline (latency values)."""
        entries = self._fetch_history_entries(proxy_id, limit=30)
        points = []
        for e in entries:
            if e["is_working"] and e["latency"] is not None:
                points.append(float(e["latency"]))
            else:
                points.append(0.0)
        return points

    def get_summary_stats(self, proxy_id: str) -> Dict[str, Any]:
        """Get summary statistics for a proxy."""
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
        """Calculate reliability score."""
        stats = self.get_summary_stats(proxy_id)
        return float(stats.get("success_rate", 0.0))

    def get_trend_data(self, proxy_id: str, points: int = 30) -> Dict[str, Any]:
        """Get trend data for charting."""
        history = self.get_proxy_history(proxy_id)
        return HistoryAnalytics.get_trend_data(history, points)

    def cleanup_old_data(self, days: int = 30) -> int:
        """
        Remove history data older than specified days.
        """
        if not self.storage:
            return 0

        try:
            cutoff = int(
                (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
            )
            sql = "DELETE FROM proxy_history WHERE timestamp < ?"
        removed = 0

            if hasattr(self.storage, "execute_write"):
            # Assumes execute_write is modified to return rowcount if supported
            # For now, it returns None or result, so we default to 0 if not supported
            res = self.storage.execute_write(sql, (cutoff,))
            if isinstance(res, int):
                removed = res
            else:
                # If underlying storage doesn't return count, we can't report it easily
                # but we prefer returning 0 over -1 to match type signature if strict
                removed = 0
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
        """Merge another history tracker (DB) into this one."""
        if not self.storage or not other.storage:
            return
        if hasattr(self.storage, "merge_from") and hasattr(other.storage, "db_path"):
            self.storage.merge_from(other.storage.db_path)

    def get_bulk_stats(self, proxy_ids: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Get stats for multiple proxies efficiently.
        Returns a dict mapping proxy_id to {'reliability': float, 'uptime': float}.
        """
        results: Dict[str, Dict[str, float]] = {}
        if not self.storage:
            return results

        try:
            conn = self.storage.get_connection()
            # Aggregate stats directly in DB
            query = """
                SELECT proxy_id,
                       AVG(is_working) as reliability
                FROM proxy_history
                GROUP BY proxy_id
            """
            cursor = conn.execute(query)
            for row in cursor:
                pid, rel = row
                results[pid] = {"reliability": float(rel), "uptime": float(rel) * 100.0}

        except Exception as e:
            logger.error(f"Failed to get bulk stats: {e}")

        return results

    def _load_all_history(self) -> Dict[str, Any]:
        """
        Load all history from DB into dictionary format.
        [WARNING] This method loads the ENTIRE dataset into memory.
        It should only be used for small-scale exports or debugging.
        For large datasets (>100k entries), refactor to use streaming/generators.
        """
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

                # Limit total rows to prevent catastrophic OOM in production
                MAX_ROWS = 500000
                row_count = 0

                while True:
                    batch = cursor.fetchmany(1000)
                    if not batch:
                        break

                    for row in batch:
                        row_count += 1
                        if row_count > MAX_ROWS:
                            logger.warning(
                                f"History export truncated at {MAX_ROWS} rows to prevent OOM."
                            )
                            return history_data

                        pid, ts, working, lat, cc, reason = row
                        if pid not in history_data:
                            # Populate address/port with defaults to prevent KeyError in exporter
                            history_data[pid] = {
                                "id": pid,
                                "protocol": "unknown",
                                "address": "0.0.0.0",  # Fallback
                                "port": 0,  # Fallback
                                "entries": [],
                            }

                        ts_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

                        entry = {
                            "timestamp": ts_iso,
                            "is_working": bool(working),
                            "latency": lat,
                            "country": cc,
                            "error": reason,
                        }
                        history_data[pid]["entries"].append(entry)
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Failed to load history from DB: {e}")

        return history_data

    def export_for_visualization(self, output_path: Any) -> None:
        """
        Export history data for visualization.

        [OPTIMIZED] Uses _load_all_history for now but ensures output_path is Path.
        For massive scale, HistoryExporter should be updated to accept a generator/cursor.
        Given current constraints, we stick to memory load but wrapped safely.
        """
        # Ensure path is Path object
        from pathlib import Path

        if not isinstance(output_path, Path):
            output_path = Path(output_path)

        # If file is too large, skip or truncate?
        # Ideally we refactor HistoryExporter, but that's outside current scope.
        # We rely on _load_all_history MAX_ROWS limit to prevent crash.
        data = self._load_all_history()
        HistoryExporter.export_for_visualization(data, output_path)

    def export_active_proxy_trend(self, output_path: Any) -> None:
        """Export active proxy trend."""
        # Ensure path is Path object
        from pathlib import Path

        if not isinstance(output_path, Path):
            output_path = Path(output_path)

        data = self._load_all_history()
        HistoryExporter.export_active_proxy_trend(data, output_path)

    def close(self):
        """
        Closes the underlying storage connection.
        """
        if self.storage:
            self.storage.close()
