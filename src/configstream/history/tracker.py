import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from ..models import Proxy
from ..quality.storage import QualityStorage

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

    def export_for_visualization(self, output_path: Any) -> None:
        """Export history data for visualization."""
        # Placeholder for now
        pass

    def export_active_proxy_trend(self, output_path: Any) -> None:
        """Export active proxy trend."""
        # Placeholder for now
        pass

    def close(self):
        """
        Closes the underlying storage connection.
        """
        if self.storage:
            self.storage.close()
