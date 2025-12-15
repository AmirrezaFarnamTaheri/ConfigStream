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

logger = logging.getLogger(__name__)

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

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            # Default path if none provided (e.g. from pipeline)
            db_path = Path("data/source_quality.db")
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

        consecutive_failures = 0 if working > 0 else 1
        trust_score = 50.0

        stats = {
            "total_fetched": fetched,
            "total_working": working,
            "consecutive_failures": consecutive_failures,
            "last_checked": int(datetime.now(timezone.utc).timestamp()),
            "reliability_score": reliability,
            "diversity_score": diversity,
            "trust_score": trust_score,
        }
        self.upsert_stats(url, stats)

    def should_fetch(self, url: str) -> bool:
        """
        Determines if a source should be fetched based on its state.
        """
        state = self.get_source_state(url)
        if not state:
            return True

        # state: (status, last_checked, consecutive_failures, reliability_score, total_fetched, total_working)
        status = state[0]
        if status == "dead":
            return False
        if status == "probation":
            last_checked = state[1]
            # Retry every 6 hours
            if (datetime.now(timezone.utc).timestamp() - last_checked) < (6 * 3600):
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
            }
            self.upsert_stats(url, init_stats)

    def report_failure(self, url: str):
        """
        Legacy method called by orchestrator.py.
        Records a failed fetch for a source, incrementing failure count.
        """
        state = self.get_source_state(url)
        current_failures = 0
        if state:
            # state: (status, last_checked, consecutive_failures, ...)
            current_failures = state[2] if len(state) > 2 else 0

        stats = {
            "consecutive_failures": current_failures + 1,
            "last_checked": int(datetime.now(timezone.utc).timestamp()),
        }
        self.upsert_stats(url, stats)
