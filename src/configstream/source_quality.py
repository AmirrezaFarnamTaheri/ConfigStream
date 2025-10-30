"""
Proxy Source Quality Scoring System.

Tracks and scores proxy sources based on their performance
to focus crawling on high-quality sources.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
from datetime import datetime, timezone

from .models import Proxy

logger = logging.getLogger(__name__)


class SourceQualityTracker:
    """Tracks quality metrics for proxy sources."""

    def __init__(self, db_path: Path = Path("data/source_quality.json")):
        """
        Initialize source quality tracker.

        Args:
            db_path: Path to store quality metrics
        """
        self.db_path = Path(db_path)  # Ensure Path object
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.quality_data = self.load_quality_data()

    def load_quality_data(self) -> Dict[str, Any]:
        """Load quality data from disk."""
        if self.db_path.exists():
            try:
                data: Dict[str, Any] = json.loads(self.db_path.read_text())
                return data
            except Exception as e:
                logger.warning("Failed to load source quality data: %s", e)
        return {}

    def save_quality_data(self) -> None:
        """Save quality data to disk."""
        self.db_path.write_text(json.dumps(self.quality_data, indent=2))

    def update_source_quality(self, source: str, proxies: List[Proxy]) -> None:
        """
        Update quality metrics for a source.

        Args:
            source: Source URL or identifier
            proxies: List of proxies from this source
        """
        if source not in self.quality_data:
            self.quality_data[source] = {
                "total_fetches": 0,
                "total_proxies": 0,
                "working_proxies": 0,
                "avg_latency": 0,
                "last_updated": None,
                "success_rate": 0.0,
            }

        stats = self.quality_data[source]
        stats["total_fetches"] += 1
        stats["total_proxies"] += len(proxies)

        working = [p for p in proxies if p.is_working]
        stats["working_proxies"] += len(working)

        if working:
            latencies = [p.latency for p in working if p.latency]
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                # Running average
                if stats["avg_latency"] == 0:
                    stats["avg_latency"] = avg_latency
                else:
                    stats["avg_latency"] = stats["avg_latency"] * 0.7 + avg_latency * 0.3

        stats["success_rate"] = (
            stats["working_proxies"] / stats["total_proxies"] if stats["total_proxies"] > 0 else 0.0
        )
        stats["last_updated"] = datetime.now(timezone.utc).isoformat()

        self.save_quality_data()

    def get_source_score(self, source: str) -> float:
        """
        Calculate quality score for a source (0-100).

        Args:
            source: Source URL or identifier

        Returns:
            Quality score between 0 and 100
        """
        if source not in self.quality_data:
            return 50.0  # Neutral score for new sources

        stats = self.quality_data[source]

        # Success rate (60 points)
        score = stats["success_rate"] * 60.0

        # Latency (30 points) - lower is better
        if stats["avg_latency"] > 0:
            # Invert latency: 0-500ms = 30pts, >5000ms = 0pts
            latency_score = max(0, 30.0 * (1 - min(stats["avg_latency"] / 5000, 1)))
            score += latency_score
        else:
            score += 15.0  # Neutral

        # Consistency (10 points) - based on fetch count
        if stats["total_fetches"] >= 10:
            score += 10.0
        elif stats["total_fetches"] >= 5:
            score += 5.0

        result: float = round(min(score, 100.0), 2)
        return result

    def get_top_sources(self, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Get top quality sources.

        Args:
            limit: Number of sources to return

        Returns:
            List of (source, score) tuples
        """
        scored_sources = [
            (source, self.get_source_score(source)) for source in self.quality_data.keys()
        ]
        scored_sources.sort(key=lambda x: x[1], reverse=True)
        return scored_sources[:limit]

    def get_quality_report(self) -> Dict[str, Any]:
        """
        Generate quality report for all sources.

        Returns:
            Dictionary with quality statistics
        """
        return {
            "total_sources": len(self.quality_data),
            "top_sources": self.get_top_sources(5),
            "source_details": {
                source: {
                    "score": self.get_source_score(source),
                    "success_rate": f"{stats['success_rate']*100:.1f}%",
                    "avg_latency": f"{stats['avg_latency']:.0f}ms",
                    "total_proxies": stats["total_proxies"],
                }
                for source, stats in self.quality_data.items()
            },
        }
