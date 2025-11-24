"""
Proxy History Tracker.

Tracks proxy performance metrics over time to enable
trend analysis and reliability visualization.
Refactored to use submodules.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone, timedelta

from .models import Proxy
from .history.storage import HistoryStorage
from .history.analytics import HistoryAnalytics
from .history.export import HistoryExporter

logger = logging.getLogger(__name__)


class ProxyHistoryTracker:
    """Tracks historical performance data for proxies."""

    def __init__(
        self,
        history_path: Path = Path("data/proxy_history.json"),
        max_entries: int = 100,
    ):
        """
        Initialize history tracker.

        Args:
            history_path: Path to store history data
            max_entries: Maximum number of historical entries to keep per proxy
        """
        self.history_path = Path(history_path)
        self.max_entries = max_entries
        self.storage = HistoryStorage(self.history_path)
        self.history_data = self.storage.load_history()

    def record_test_result(self, proxy: Proxy) -> None:
        """
        Record a test result for a proxy.

        Args:
            proxy: Proxy with test results
        """
        # Use config as unique identifier
        proxy_id = proxy.config

        if proxy_id not in self.history_data:
            self.history_data[proxy_id] = {
                "protocol": proxy.protocol,
                "address": proxy.address,
                "port": proxy.port,
                "entries": [],
            }

        # Create entry
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_working": proxy.is_working,
            "latency": proxy.latency,
            "country": proxy.country,
        }

        # Add entry and trim if needed
        self.history_data[proxy_id]["entries"].append(entry)
        if len(self.history_data[proxy_id]["entries"]) > self.max_entries:
            self.history_data[proxy_id]["entries"] = self.history_data[proxy_id][
                "entries"
            ][-self.max_entries :]

    def save(self) -> None:
        """Save the history data to disk."""
        self.storage.save_history(self.history_data)

    def get_proxy_history(self, config: str) -> Optional[Dict[str, Any]]:
        """Get history for a specific proxy."""
        return self.history_data.get(config)

    def get_reliability_score(self, config: str, lookback_days: int = 7) -> float:
        """Calculate reliability score."""
        history = self.get_proxy_history(config)
        return HistoryAnalytics.get_reliability_score(history, lookback_days)

    def get_trend_data(self, config: str, points: int = 30) -> Dict[str, Any]:
        """Get trend data for charting."""
        history = self.get_proxy_history(config)
        return HistoryAnalytics.get_trend_data(history, points)

    def get_history(self, config: str) -> List[float]:
        """Get simplified history (last 10 data points)."""
        history = self.get_proxy_history(config)
        return HistoryAnalytics.get_history_points(history)

    def get_summary_stats(self, config: str) -> Dict[str, Any]:
        """Get summary statistics for a proxy."""
        history = self.get_proxy_history(config)
        return HistoryAnalytics.get_summary_stats(history)

    def export_for_visualization(
        self, output_path: Path = Path("data/proxy_history_viz.json")
    ) -> None:
        """Export history data in format optimized for web visualization."""
        HistoryExporter.export_for_visualization(self.history_data, output_path)

    def export_active_proxy_trend(
        self,
        output_path: Path = Path("data/active_proxy_trend.json"),
        hours_to_track: int = 168,
        bucket_minutes: int = 60,
    ) -> None:
        """Aggregates historical data to show active proxies trend."""
        HistoryExporter.export_active_proxy_trend(
            self.history_data, output_path, hours_to_track, bucket_minutes
        )

    def cleanup_old_data(self, days: int = 30) -> int:
        """
        Remove history data older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of proxies removed
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        removed = 0

        for config in list(self.history_data.keys()):
            entries = self.history_data[config]["entries"]

            # Filter out old entries
            recent = [
                e
                for e in entries
                if datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
                > cutoff
            ]

            if not recent:
                # Remove proxy if no recent data
                del self.history_data[config]
                removed += 1
            else:
                self.history_data[config]["entries"] = recent

        if removed > 0:
            self.save()
            logger.info("Cleaned up history for %d proxies", removed)

        return removed
