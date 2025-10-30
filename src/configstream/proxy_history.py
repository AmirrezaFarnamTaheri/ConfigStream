"""
Proxy History Tracker.

Tracks proxy performance metrics over time to enable
trend analysis and reliability visualization.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, cast
from datetime import datetime, timezone

from .models import Proxy

logger = logging.getLogger(__name__)


class ProxyHistoryTracker:
    """Tracks historical performance data for proxies."""

    def __init__(
        self, history_path: Path = Path("data/proxy_history.json"), max_entries: int = 100
    ):
        """
        Initialize history tracker.

        Args:
            history_path: Path to store history data
            max_entries: Maximum number of historical entries to keep per proxy
        """
        self.history_path = Path(history_path)
        self.max_entries = max_entries
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_data = self._load_history()

    def _load_history(self) -> Dict[str, Any]:
        """Load history data from disk."""
        if self.history_path.exists():
            try:
                data: Dict[str, Any] = json.loads(self.history_path.read_text())
                return data
            except Exception as e:
                logger.warning("Failed to load proxy history: %s", e)
        return {}

    def _save_history(self) -> None:
        """Save history data to disk."""
        try:
            self.history_path.write_text(json.dumps(self.history_data, indent=2))
        except Exception as e:
            logger.error("Failed to save proxy history: %s", e)

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
            self.history_data[proxy_id]["entries"] = self.history_data[proxy_id]["entries"][
                -self.max_entries :
            ]

        self._save_history()

    def get_proxy_history(self, config: str) -> Optional[Dict[str, Any]]:
        """
        Get history for a specific proxy.

        Args:
            config: Proxy configuration string

        Returns:
            History data or None
        """
        result = self.history_data.get(config)
        return cast(Optional[Dict[str, Any]], result)

    def get_reliability_score(self, config: str, lookback_days: int = 7) -> float:
        """
        Calculate reliability score based on recent history.

        Args:
            config: Proxy configuration string
            lookback_days: Number of days to look back

        Returns:
            Reliability score 0.0-1.0
        """
        history = self.get_proxy_history(config)
        if not history or not history["entries"]:
            return 0.5  # Neutral for unknown

        # Calculate success rate from recent entries
        entries = history["entries"]
        working_count = sum(1 for e in entries if e["is_working"])

        return working_count / len(entries) if entries else 0.5

    def get_trend_data(self, config: str, points: int = 30) -> Dict[str, Any]:
        """
        Get trend data for charting.

        Args:
            config: Proxy configuration string
            points: Number of data points to return

        Returns:
            Dictionary with timestamps, latencies, and status
        """
        history = self.get_proxy_history(config)
        if not history or not history["entries"]:
            return {"timestamps": [], "latencies": [], "status": []}

        entries = history["entries"][-points:]

        return {
            "timestamps": [e["timestamp"] for e in entries],
            "latencies": [e["latency"] if e["latency"] else 0 for e in entries],
            "status": [1 if e["is_working"] else 0 for e in entries],
        }

    def get_summary_stats(self, config: str) -> Dict[str, Any]:
        """
        Get summary statistics for a proxy.

        Args:
            config: Proxy configuration string

        Returns:
            Dictionary with summary statistics
        """
        history = self.get_proxy_history(config)
        if not history or not history["entries"]:
            return {
                "total_tests": 0,
                "success_rate": 0.0,
                "avg_latency": 0,
                "min_latency": 0,
                "max_latency": 0,
                "uptime_percentage": 0.0,
            }

        entries = history["entries"]
        latencies = [e["latency"] for e in entries if e["latency"] is not None]
        working = [e for e in entries if e["is_working"]]

        return {
            "total_tests": len(entries),
            "success_rate": len(working) / len(entries) if entries else 0.0,
            "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
            "min_latency": min(latencies) if latencies else 0,
            "max_latency": max(latencies) if latencies else 0,
            "uptime_percentage": (len(working) / len(entries) * 100) if entries else 0.0,
        }

    def export_for_visualization(
        self, output_path: Path = Path("data/proxy_history_viz.json")
    ) -> None:
        """
        Export history data in format optimized for web visualization.

        Args:
            output_path: Path to output file
        """
        viz_data = {}

        # Process each proxy
        for config, data in self.history_data.items():
            if not data["entries"]:
                continue

            # Get trend data and summary stats
            trend = self.get_trend_data(config, points=50)
            stats = self.get_summary_stats(config)

            viz_data[config] = {
                "protocol": data["protocol"],
                "address": data["address"],
                "port": data["port"],
                "trend": trend,
                "stats": stats,
                "last_test": data["entries"][-1]["timestamp"] if data["entries"] else None,
            }

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(viz_data, indent=2))
        logger.info("Exported history visualization data to %s", output_path)

    def cleanup_old_data(self, days: int = 30) -> int:
        """
        Remove history data older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of proxies removed
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        removed = 0

        for config in list(self.history_data.keys()):
            entries = self.history_data[config]["entries"]

            # Filter out old entries
            recent = [
                e
                for e in entries
                if datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) > cutoff
            ]

            if not recent:
                # Remove proxy if no recent data
                del self.history_data[config]
                removed += 1
            else:
                self.history_data[config]["entries"] = recent

        if removed > 0:
            self._save_history()
            logger.info("Cleaned up history for %d proxies", removed)

        return removed
