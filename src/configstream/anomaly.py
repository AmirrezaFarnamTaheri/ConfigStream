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
        Uses Z-score for detecting outliers when sufficient history exists.

        Returns:
            (is_safe: bool, reason: str)
        """
        # Always allow empty or small batches
        if current_count <= 5:
            return True, "Small Batch"

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get last 30 fetches
                rows = conn.execute(
                    "SELECT count FROM history WHERE url = ? ORDER BY timestamp DESC LIMIT 30",
                    (url,),
                ).fetchall()

                if not rows:
                    return True, "New Source"

                counts = [r[0] for r in rows]
                n = len(counts)
                avg = statistics.mean(counts)

                # Logic: Detect Massive Spikes
                # Only apply logic if the source is somewhat established (avg > 10)
                if avg > 10 and n > 5:
                    stdev = statistics.stdev(counts) if n > 1 else 0

                    # Z-Score Check (if variance is zero, avoid div/0)
                    if stdev > 0:
                        z_score = (current_count - avg) / stdev
                        if z_score > 3.0:  # > 3 SDs away is suspicious
                            # Double check: sometimes absolute count isn't insane
                            # If it's < 2x average, maybe ignore Z-score (natural variance)
                            if current_count > (avg * 2.5):
                                return False, f"Z-Score Spike ({z_score:.2f})"
                    else:
                        # Zero variance history (always returns X, now returns Y)
                        if current_count > (avg * 3):
                            return (
                                False,
                                f"Sudden Spike (Prev exact: {avg}, Now: {current_count})",
                            )

                elif avg <= 10 and current_count > 200:
                    # Small source suddenly returns huge amount
                    return False, "Massive Spike for Small Source"

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
                # Prune old history (keep last 100)
                conn.execute(
                    """DELETE FROM history WHERE url = ? AND timestamp NOT IN
                    (SELECT timestamp FROM history WHERE url = ? ORDER BY timestamp DESC LIMIT 100)""",
                    (url, url),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to record anomaly stats: {e}")
