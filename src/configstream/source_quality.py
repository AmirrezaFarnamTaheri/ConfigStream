# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Facade for Source Quality module.
Provides backward compatibility for the pipeline.
"""

from typing import Any, Optional, Dict
from pathlib import Path
from datetime import datetime, timezone
import logging
from dataclasses import dataclass

from .quality.storage import QualityStorage
from .quality.scoring import calculate_diversity_score
from .config import AppSettings

logger = logging.getLogger(__name__)

# Cache settings to avoid repeated pydantic_settings instantiation in hot-path methods
_SETTINGS_CACHE = AppSettings()

__all__ = ["SourceQualityTracker", "calculate_diversity_score"]


@dataclass
class SourceHealth:
    url: str
    failures: int = 0
    last_success: float = 0.0
    last_failure: float = 0.0
    status: str = "active"  # active, probation, dead


class SourceQualityTracker(QualityStorage):
    """
    Adapter class to make QualityStorage compatible with legacy SourceQualityTracker calls.
    """

    @staticmethod
    def _derive_status(
        consecutive_failures: int, reason: Optional[str], settings: AppSettings
    ) -> str:
        """Determine source status based on failure count and reason."""
        probation_threshold = max(1, int(settings.SOURCE_PROBATION_FAILURES))
        dead_threshold = max(
            probation_threshold + 1, int(settings.SOURCE_DEAD_FAILURES)
        )

        if reason:
            permanent_signals = (
                "Permanent Error: 404",
                "Permanent Error: 410",
                "Malformed GitHub URL",
            )
            if any(signal in reason for signal in permanent_signals):
                return "dead"

        if consecutive_failures >= dead_threshold:
            return "dead"
        if consecutive_failures >= probation_threshold:
            return "probation"
        return "active"

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            # Default path if none provided (e.g. from pipeline)
            db_path = Path(_SETTINGS_CACHE.QUALITY_DB_PATH)
        super().__init__(db_path)

        # Legacy in-memory fallback for compatibility if needed
        self.sources: Dict[str, SourceHealth] = {}

    def update(
        self,
        url: str,
        fetched: Optional[int] = None,
        working: Optional[int] = None,
        diversity: Optional[float] = None,
        reliability: Optional[float] = None,
        # Legacy keyword args mapping
        fetched_count: Optional[int] = None,
        working_count: Optional[int] = None,
        diversity_score: Optional[float] = None,
        reliability_score: Optional[float] = None,
    ):
        """
        Legacy update method called by consumers and tests.
        Maps arguments to the new dictionary-based upsert_stats.
        """
        # Map legacy kwargs to new args
        if fetched is None:
            fetched = fetched_count or 0
        if working is None:
            working = working_count or 0
        if diversity is None:
            diversity = diversity_score or 0.0
        if reliability is None:
            reliability = reliability_score

        # Calculate reliability if not provided
        if reliability is None:
            reliability = (working / fetched * 100) if fetched > 0 else 0.0

        state = self.get_source_state(url)
        prev_failures = state[2] if state and len(state) > 2 else 0

        if working > 0:
            consecutive_failures = 0
        else:
            consecutive_failures = prev_failures + 1

        trust_score = 50.0
        settings = _SETTINGS_CACHE
        prev_status = state[0] if state else "active"
        if working > 0:
            status = "active"
        elif prev_status == "dead":
            status = "dead"
        else:
            status = self._derive_status(consecutive_failures, None, settings)

        stats = {
            "total_fetched": fetched,
            "total_working": working,
            "consecutive_failures": consecutive_failures,
            "last_checked": int(datetime.now(timezone.utc).timestamp()),
            "reliability_score": reliability,
            "diversity_score": diversity,
            "trust_score": trust_score,
            "status": status,
        }
        self.upsert_stats(url, stats)

    def should_fetch(self, url: str) -> bool:
        """
        Determines if a source should be fetched based on its state.

        [FIX] Dead sources now have a "resurrection" window (7 days by default)
        to prevent permanent death spirals where a temporarily unavailable source
        is never retried.  Permanent failures (404/410) remain permanently dead.
        """
        state = self.get_source_state(url)
        if not state:
            return True

        # state: (status, last_checked, consecutive_failures, reliability_score, total_fetched, total_working)
        status = state[0]
        last_checked = state[1] if len(state) > 1 else 0
        now = datetime.now(timezone.utc).timestamp()
        settings = _SETTINGS_CACHE

        if status == "dead":
            # [FIX] Resurrection window: allow retry after a long cooling period
            # unless the source had a permanent error (consecutive_failures >= 100
            # is used as a sentinel for permanent 404/410 errors)
            consecutive_failures = state[2] if len(state) > 2 else 0
            if consecutive_failures >= 100:
                # Truly permanent failure (404/410) - never retry
                return False
            resurrection_hours = getattr(
                settings, "SOURCE_RESURRECTION_HOURS", 168
            )  # 7 days
            if (now - last_checked) >= (resurrection_hours * 3600):
                logger.info(f"Resurrecting dead source for retry: {url[:60]}...")
                return True
            return False

        if status == "probation":
            # Retry at the configured pipeline interval
            retry_seconds = settings.UPDATE_INTERVAL_HOURS * 3600
            if (now - last_checked) < retry_seconds:
                return False
        return True

    def get_source_score(self, url: str) -> float:
        """
        Legacy method to retrieve a score for a source.
        Returns reliability score or a computed metric.
        """
        state = self.get_source_state(url)
        if not state:
            return 50.0  # Default

        # state[3] is reliability_score
        return float(state[3])

    def report_success(self, url: str):
        """
        Legacy method called by orchestrator.py.
        Records a successful fetch for a source, resetting failure count.
        """
        state = self.get_source_state(url)
        if state:
            # Reset consecutive failures on success
            update_stats: Dict[str, Any] = {
                "consecutive_failures": 0,
                "last_checked": int(datetime.now(timezone.utc).timestamp()),
                "status": "active",
            }
            self.upsert_stats(url, update_stats)
        else:
            # New source - initialize with success
            init_stats: Dict[str, Any] = {
                "consecutive_failures": 0,
                "last_checked": int(datetime.now(timezone.utc).timestamp()),
                "total_fetched": 0,
                "total_working": 0,
                "reliability_score": 50.0,
                "diversity_score": 0.0,
                "trust_score": 50.0,
                "status": "active",
            }
            self.upsert_stats(url, init_stats)

    def report_failure(self, url: str, reason: Optional[str] = None):
        """
        Legacy method called by orchestrator.py.
        Records a failed fetch for a source, incrementing failure count.
        """
        settings = _SETTINGS_CACHE
        state = self.get_source_state(url)
        current_failures = 0
        if state:
            # state: (status, last_checked, consecutive_failures, ...)
            current_failures = state[2] if len(state) > 2 else 0

        new_failures = current_failures + 1
        status = self._derive_status(new_failures, reason, settings)
        stats = {
            "consecutive_failures": new_failures,
            "last_checked": int(datetime.now(timezone.utc).timestamp()),
            "status": status,
        }
        self.upsert_stats(url, stats)

    def get_worst_sources(self, limit: int = 5) -> list[Dict[str, Any]]:
        """
        Retrieves the worst performing sources based on reliability score and consecutive failures.
        Returns a list of dictionaries.
        """
        return self.get_worst_performing(limit=limit)
