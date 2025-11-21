"""
Anomaly Detector.
Identifies suspicious spikes or drops in source content volume to prevent
cache poisoning and spam attacks.
Uses Isolation Forest for robust outlier detection when sufficient data exists.
"""

import sqlite3
import logging
import statistics
import time
import numpy as np
from pathlib import Path
from typing import Tuple
from sklearn.ensemble import IsolationForest

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
        Uses Isolation Forest for detecting outliers when sufficient history exists (n > 15).
        Falls back to Z-score for smaller datasets.

        Returns:
            (is_safe: bool, reason: str)
        """
        # Always allow empty or small batches
        if current_count <= 5:
            return True, "Small Batch"

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get last 50 fetches (increased history depth for ML)
                rows = conn.execute(
                    "SELECT count FROM history WHERE url = ? ORDER BY timestamp DESC LIMIT 50",
                    (url,),
                ).fetchall()

                if not rows:
                    return True, "New Source"

                counts = [r[0] for r in rows]
                n = len(counts)
                avg = statistics.mean(counts)

                # Strategy: Use Isolation Forest if we have enough data points
                if n >= 15:
                    try:
                        # Prepare data for Isolation Forest (needs 2D array)
                        X = np.array(counts).reshape(-1, 1)

                        # Fit Isolation Forest
                        # contamination='auto' lets it decide outlier proportion
                        clf = IsolationForest(random_state=42, contamination=0.05)
                        clf.fit(X)

                        # Predict on current value
                        prediction = clf.predict([[current_count]])

                        # -1 is outlier, 1 is inlier
                        if prediction[0] == -1:
                            # Double check: If it's just a higher yield but within reason (< 2x max historic), let it slide
                            max_historic = max(counts)
                            if current_count > (max_historic * 2.0):
                                return (
                                    False,
                                    f"Isolation Forest Outlier (Count: {current_count})",
                                )
                            elif (
                                current_count < (min(counts) * 0.5)
                                and current_count > 20
                            ):
                                # Significant drop is usually safe but might indicate issue
                                # We generally care about poisoning (spikes)
                                logger.debug(
                                    f"Significant drop detected for {url}: {current_count} vs avg {avg}. Ignoring as not a spike."
                                )

                    except Exception as ml_err:
                        logger.warning(
                            f"ML Anomaly check failed, falling back to Z-Score: {ml_err}"
                        )
                        # Fall through to Z-Score logic

                # Logic: Detect Massive Spikes (Fallback Z-Score / Simple Heuristics)
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
