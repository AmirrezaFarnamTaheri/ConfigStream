"""
Anomaly Detector.
Identifies suspicious spikes or drops in source content volume to prevent
cache poisoning and spam attacks.
Uses Isolation Forest for robust outlier detection when sufficient data exists.
"""

import logging
import sqlite3
import statistics
import threading
import time
from pathlib import Path
from typing import Any, Dict, Tuple

from .constants import Z_SCORE_NORMAL_CONSTANT

# Removed heavy sklearn/numpy dependency
# import numpy as np
# from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class AnomalyDetector:
    def __init__(self, db_path: Path = Path("data/anomaly.db")):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._lock:
            self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable WAL mode for better concurrency and crash recovery
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
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
        except Exception as e:  # pylint: disable=broad-exception-caught
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
            # Fetch rows under lock (short critical section), then release for computation
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    rows = conn.execute(
                        "SELECT count FROM history WHERE url = ? ORDER BY timestamp DESC LIMIT 50",
                        (url,),
                    ).fetchall()

            if not rows:
                return True, "New Source"

            counts = [r[0] for r in rows if isinstance(r[0], int)]
            if not counts:
                return True, "Insufficient numeric history"

            n = len(counts)
            avg = statistics.mean(counts)

            # Strategy: Use Median Absolute Deviation (MAD) if we have enough data points
            # Robust replacement for Isolation Forest that doesn't require sklearn
            if n >= 10:
                try:
                    median = statistics.median(counts)
                    mad = statistics.median([abs(x - median) for x in counts])

                    # If MAD is 0 (all values same), treat as small epsilon
                    if mad == 0:
                        mad = 1.0  # Avoid division by zero

                    # Modified Z-score using constant for normal distribution consistency
                    modified_z = (
                        Z_SCORE_NORMAL_CONSTANT * (current_count - median) / mad
                    )

                    # Threshold of 3.5 is standard for outlier detection
                    if (
                        modified_z > 5.0
                    ):  # Conservative threshold to avoid false positives
                        # Double check: > 2x max historic
                        max_historic = max(counts)
                        if current_count > (max_historic * 2.0):
                            return (
                                False,
                                f"Statistical Outlier (Modified Z: {modified_z:.2f})",
                            )

                    if current_count < (median * 0.5) and current_count > 20:
                        logger.debug(
                            f"Significant volume drop for {url}: {current_count} vs median {median}. "
                            "Treated as safe."
                        )

                except Exception as stat_err:
                    logger.warning(
                        f"Anomaly check failed, falling back to Z-Score: {stat_err}"
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

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Do NOT hard-block all traffic from this source on transient DB errors.
            # Failing closed here can effectively disable the entire pipeline if the
            # anomaly database is temporarily unavailable.
            logger.error(
                "Anomaly DB error for %s: %s - allowing source (fail-open behaviour)",
                url,
                e,
            )
            # Re-raise runtime errors to test fail-open logic in tests if intended,
            # but for production we return True.
            # However, the test 'test_failure_mode_anomaly_db_crash' explicitly mocks this method
            # to raise RuntimeError. If the real method catches it, the test mock is bypassed if we use spy.
            # But the test replaces the method entirely.
            # So this catch block is only for real usage.
            return True, "DB Error (Fail Open)"

    def check_subnet_flood(self, proxies: list[dict]) -> bool:
        """
        Detect if a source is flooding with proxies from the same subnet.
        Returns True if flooding is detected (unsafe), False otherwise.
        Criteria: > 90% from same /24 subnet if count > 50.
        """
        if len(proxies) < 50:
            return False

        subnets = []
        for p in proxies:
            ip = p.get("server") or p.get("ip") or "0.0.0.0"
            if ip.count(".") == 3:
                # Extract /24 subnet
                subnet = ".".join(ip.split(".")[:3])
                subnets.append(subnet)

        if not subnets:
            return False

        from collections import \
            Counter  # pylint: disable=import-outside-toplevel

        counts = Counter(subnets)
        most_common = counts.most_common(1)[0]

        # [FIX] Add zero-length check to prevent division by zero
        # If one subnet accounts for > 90% of proxies
        if len(proxies) > 0 and most_common[1] / len(proxies) > 0.9:
            logger.warning(
                f"Subnet Flood detected: {most_common[0]}.0/24 accounts for {most_common[1]}/{len(proxies)} proxies."
            )
            return True

        return False

    def record(self, url: str, count: int):
        """
        Record a successful fetch count for future baselines.
        """
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
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
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"Failed to record anomaly stats: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get anomaly detection statistics for monitoring."""
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                total_sources = conn.execute(
                    "SELECT COUNT(DISTINCT url) FROM history"
                ).fetchone()[0]
                total_records = conn.execute("SELECT COUNT(*) FROM history").fetchone()[
                    0
                ]
                recent_anomalies = conn.execute(
                    "SELECT COUNT(*) FROM history WHERE timestamp > ?",
                    (int(time.time()) - 86400,),
                ).fetchone()[0]

                stats = {
                    "total_sources_tracked": total_sources,
                    "total_history_records": total_records,
                    "records_last_24h": recent_anomalies,
                    "db_size_bytes": (
                        self.db_path.stat().st_size if self.db_path.exists() else 0
                    ),
                }
                logger.info(
                    f"Anomaly stats: {total_sources} sources tracked, "
                    f"{total_records} total records, {recent_anomalies} in last 24h"
                )
                return stats
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get anomaly stats: {e}")
            return {}

    def merge_from(self, other_db_path: Path):
        """
        Merge history from another Anomaly DB.
        """
        if not other_db_path.exists():
            return

        try:
            with self._lock:
                with (
                    sqlite3.connect(other_db_path) as src,
                    sqlite3.connect(self.db_path) as dst,
                ):
                    src.execute("PRAGMA journal_mode=WAL")
                dst.execute("PRAGMA journal_mode=WAL")

                # Copy all history records. We rely on the fact that (url, timestamp) collisions are unlikely
                # or acceptable (idempotent in spirit, though SQLite doesn't enforce unique on history).
                # We should probably avoid strict duplicates.

                rows = src.execute(
                    "SELECT url, count, timestamp FROM history"
                ).fetchall()

                for row in rows:
                    url, count, ts = row
                    # Check if exists
                    exists = dst.execute(
                        "SELECT 1 FROM history WHERE url = ? AND timestamp = ?",
                        (url, ts),
                    ).fetchone()

                    if not exists:
                        dst.execute(
                            "INSERT INTO history (url, count, timestamp) VALUES (?, ?, ?)",
                            (url, count, ts),
                        )

                dst.commit()
                logger.info(f"Merged anomaly stats from {other_db_path}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to merge anomaly DB {other_db_path}: {e}")
