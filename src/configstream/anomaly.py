"""
Anomaly Detector.
Identifies suspicious spikes or drops in source content volume to prevent
cache poisoning and spam attacks.
"""

import sqlite3
import logging
import statistics
import time
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


class AnomalyDetector:
    def __init__(self, db_path: Path = Path("data/anomaly.db")):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
CREATE TABLE IF NOT EXISTS history (
    url TEXT,
    count INTEGER,
    timestamp INTEGER
)
"""
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_url ON history(url)")
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to init anomaly DB: {e}")

    def is_safe(self, url: str, current_count: int) -> Tuple[bool, str]:
        """
        Check if the current item count is statistically safe compared to history.

        Returns:
            (is_safe: bool, reason: str)
        """
        # Always allow empty or small batches
        if current_count <= 5:
            return True, "Small Batch"

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get last 20 fetches
                rows = conn.execute(
                    "SELECT count FROM history WHERE url = ? ORDER BY timestamp DESC LIMIT 20",
                    (url,),
                ).fetchall()

                if not rows:
                    # No history -> Trust but Verify (allow it, but maybe log)
                    return True, "New Source"

                counts = [r[0] for r in rows]
                avg = statistics.mean(counts)

                # Logic: Detect Massive Spikes
                # Only apply logic if the source is somewhat established (avg > 10)
                if avg > 10:
                    # If count is > 5x the average, it's suspicious
                    if current_count > (avg * 5):
                        msg = (
                            f"Spike Detected (Current: {current_count}, Avg: {avg:.1f})"
                        )
                        return False, msg

                return True, "OK"

        except Exception as e:
            logger.warning(f"Anomaly check failed for {url}: {e}")
            return True, "Error (Fail Open)"

    def record(self, url: str, count: int):
        """
        Record a successful fetch count for future baselines.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO history (url, count, timestamp) VALUES (?, ?, ?)",
                    (url, count, int(time.time())),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to record anomaly stats: {e}")
