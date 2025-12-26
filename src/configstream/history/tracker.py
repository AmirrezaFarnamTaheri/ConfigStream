import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from ..models import Proxy
from ..quality.storage import QualityStorage
from .export import HistoryExporter

logger = logging.getLogger(__name__)


class ProxyHistoryTracker:
    """
    Manages the persistent history of proxies, including:
    - Availability over time
    - Latency trends
    - Reliability scoring
    """

    def __init__(self, storage: Optional[QualityStorage] = None):
        if storage:
            self.storage = storage
        else:
            # We need a path. Assuming a default path if none provided.
            from pathlib import Path

            self.storage = QualityStorage(Path("data/history.db"))
        self.session_id = datetime.now(timezone.utc).isoformat()

    def update_history(self, proxies: List[Proxy]):
        """
        Updates the history database with the latest test results.
        """
        if not self.storage:
            logger.warning("History storage not initialized, skipping update.")
            return

        try:
            # Access the internal connection of QualityStorage
            conn = self.storage.get_connection()

            timestamp = int(datetime.now(timezone.utc).timestamp())

            data_to_insert = []
            for p in proxies:
                data_to_insert.append((
                    p.id,
                    timestamp,
                    1 if p.is_working else 0,
                    p.latency,
                    p.country_code,
                    self.session_id,
                    p.details.get("error", "") if not p.is_working else None
                ))

            conn.executemany(
                """
                INSERT INTO proxy_history (proxy_id, timestamp, is_working, latency, country_code, session_id, failure_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                data_to_insert
            )
            conn.commit()

        except Exception as e:
            logger.error(f"Failed to update proxy history: {e}")

    def get_history(self, proxy_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the history for a specific proxy.
        """
        if not self.storage:
            return []

        try:
            conn = self.storage.get_connection()
            cursor = conn.execute(
                "SELECT timestamp, is_working, latency, failure_reason FROM proxy_history WHERE proxy_id = ? ORDER BY timestamp DESC LIMIT 50",
                (proxy_id,)
            )
            return [
                {
                    "timestamp": row[0],
                    "is_working": bool(row[1]),
                    "latency": row[2],
                    "failure_reason": row[3]
                }
                for row in cursor.fetchall()
            ]
        except Exception as e:
            logger.error(f"Failed to get history for {proxy_id}: {e}")
            return []

    def save(self) -> None:
        """Save history. No-op for SQLite as it auto-commits."""
        pass

    def merge(self, other: "ProxyHistoryTracker") -> None:
        """Merge another history tracker (DB) into this one."""
        if not self.storage or not other.storage:
            return
        if hasattr(self.storage, 'merge_from') and hasattr(other.storage, 'db_path'):
             self.storage.merge_from(other.storage.db_path)

    def _load_all_history(self) -> Dict[str, Any]:
        """Load all history from DB into dictionary format."""
        if not self.storage:
            return {}

        history_data = {}
        try:
            conn = self.storage.get_connection()
            # Fetch all rows. Optimizing with fetchmany if needed, but for export we need all.
            cursor = conn.execute("SELECT proxy_id, timestamp, is_working, latency, country_code, failure_reason FROM proxy_history")

            for row in cursor:
                pid, ts, working, lat, cc, reason = row
                if pid not in history_data:
                    history_data[pid] = {
                        "id": pid,
                        "protocol": "unknown", # We don't store protocol in history table yet
                        "entries": []
                    }

                ts_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

                entry = {
                    "timestamp": ts_iso,
                    "is_working": bool(working),
                    "latency": lat,
                    "country": cc,
                    "error": reason
                }
                history_data[pid]["entries"].append(entry)

        except Exception as e:
            logger.error(f"Failed to load history from DB: {e}")

        return history_data

    def export_for_visualization(self, output_path: Any) -> None:
        """Export history data for visualization."""
        data = self._load_all_history()
        # Ensure path is Path object
        from pathlib import Path
        if not isinstance(output_path, Path):
            output_path = Path(output_path)
        HistoryExporter.export_for_visualization(data, output_path)

    def export_active_proxy_trend(self, output_path: Any) -> None:
        """Export active proxy trend."""
        data = self._load_all_history()
        from pathlib import Path
        if not isinstance(output_path, Path):
            output_path = Path(output_path)
        HistoryExporter.export_active_proxy_trend(data, output_path)

    def close(self):
        """
        Closes the underlying storage connection.
        """
        if self.storage:
            self.storage.close()
