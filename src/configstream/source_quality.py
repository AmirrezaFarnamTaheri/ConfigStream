"""
Source Quality Tracker.
Refactored to use submodules.
"""

import logging
from typing import Dict, Any
from pathlib import Path
from datetime import datetime, timedelta

from .quality.storage import QualityStorage
from .quality.scoring import (
    calculate_diversity_score,
    calculate_cooldown_hours,
    calculate_trust_score,
)

logger = logging.getLogger(__name__)


class SourceQualityTracker:
    def __init__(self, db_path: Path = Path("data/source_quality.db")):
        self.storage = QualityStorage(db_path)

    def should_fetch(self, url: str) -> bool:
        """
        Decide if a source should be fetched based on its cooldown status.
        """
        row = self.storage.get_source_state(url)
        if not row:
            return True  # New source

        # Row: status, last_checked, consecutive_failures, reliability_score, total_fetched, total_working
        status, last_ts, failures, _, _, _ = row

        if status == "disabled":
            return False

        cooldown_hours = calculate_cooldown_hours(failures)
        next_allowed = datetime.fromtimestamp(last_ts) + timedelta(hours=cooldown_hours)

        if datetime.now() < next_allowed:
            if failures > 2:
                logger.debug(
                    f"Skipping {url} (Cooldown until {next_allowed.strftime('%H:%M')})"
                )
            return False

        return True

    def update(
        self,
        url: str,
        fetched_count: int,
        working_count: int,
        diversity_score: float = 0.0,
        avg_jitter: float = 0.0,
    ):
        """
        Update the stats for a source after a pipeline run.
        """
        now = int(datetime.now().timestamp())
        is_failure = working_count == 0

        row = self.storage.get_source_state(url)

        if row:
            # status, last_checked, consecutive_failures, reliability_score, total_fetched, total_working
            _, _, cf, old_reliability, tf, tw = row

            new_tf = tf + fetched_count
            new_tw = tw + working_count
            new_cf = cf + 1 if is_failure else 0

            yield_rate = (working_count / fetched_count) if fetched_count > 0 else 0.0

            # Weighted average
            new_reliability = (old_reliability * 0.9) + (yield_rate * 100 * 0.1)
        else:
            # New
            new_tf = fetched_count
            new_tw = working_count
            new_cf = 1 if is_failure else 0

            yield_rate = (working_count / fetched_count) if fetched_count > 0 else 0.0
            new_reliability = yield_rate * 100

        trust_score = calculate_trust_score(
            new_reliability, diversity_score, new_cf, avg_jitter
        )

        stats = {
            "total_fetched": new_tf,
            "total_working": new_tw,
            "consecutive_failures": new_cf,
            "last_checked": now,
            "reliability_score": new_reliability,
            "diversity_score": diversity_score,
            "trust_score": trust_score,
        }

        self.storage.upsert_stats(url, stats)

    def record_run(self, url: str, run_data: Dict[str, Any]):
        """
        Record detailed run metadata for historical analysis.
        """
        self.storage.record_run(url, run_data)

    def get_source_score(self, url: str) -> float:
        """Get the current trust score for a source."""
        return self.storage.get_trust_score(url)

    def merge_from(self, other_db_path: Path):
        """Merge data from another SQLite database."""
        self.storage.merge_from(other_db_path)


# Helper function exposed for compatibility/imports
calculate_diversity_score = calculate_diversity_score
