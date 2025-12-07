"""
Export module for Proxy History.
Handles exporting history data for visualization and external consumption.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, cast
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from ..utils import AtomicFileWriter
from .analytics import HistoryAnalytics

logger = logging.getLogger(__name__)


class HistoryExporter:
    """Handles exporting of history data."""

    @staticmethod
    def export_for_visualization(
        history_data: Dict[str, Any],
        output_path: Path = Path("data/proxy_history_viz.json"),
    ) -> None:
        """
        Export history data in format optimized for web visualization.
        """
        viz_data = {}

        # Process each proxy
        for config, data in history_data.items():
            if not data["entries"]:
                continue

            # Get trend data and summary stats
            trend = HistoryAnalytics.get_trend_data(data, points=50)
            stats = HistoryAnalytics.get_summary_stats(data)

            viz_data[config] = {
                "protocol": data["protocol"],
                "address": data["address"],
                "port": data["port"],
                "trend": trend,
                "stats": stats,
                "last_test": (
                    data["entries"][-1]["timestamp"] if data["entries"] else None
                ),
            }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            AtomicFileWriter.write_text(output_path, json.dumps(viz_data, indent=2))
            logger.info(f"Exported history visualization data to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export visualization data: {e}")

    @staticmethod
    def export_active_proxy_trend(
        history_data: Dict[str, Any],
        output_path: Path = Path("data/active_proxy_trend.json"),
        hours_to_track: int = 168,  # 7 days
        bucket_minutes: int = 60,  # 1-hour buckets
    ) -> None:
        """
        Aggregates historical data to show the number of unique active
        proxies over time.
        """
        logger.info("Generating active proxy trend data...")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_to_track)

        buckets = defaultdict(set)
        bucket_delta = timedelta(minutes=bucket_minutes)

        for config, data in history_data.items():
            if not data.get("entries"):
                continue

            for entry in data["entries"]:
                try:
                    ts = datetime.fromisoformat(
                        entry["timestamp"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    continue

                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)

                if ts < cutoff:
                    continue

                if entry.get("is_working"):
                    bucket_start_ts = (
                        ts
                        - (ts - datetime.min.replace(tzinfo=timezone.utc))
                        % bucket_delta
                    )
                    bucket_key = bucket_start_ts.isoformat()
                    buckets[bucket_key].add(config)

        if not buckets:
            logger.warning("No working proxy data found for trend analysis.")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                AtomicFileWriter.write_text(output_path, json.dumps([], indent=2))
            except Exception as e:
                logger.error(f"Failed to write empty trend data: {e}")
            return

        trend_data = [
            {"timestamp": key, "active_count": len(proxies)}
            for key, proxies in buckets.items()
        ]

        # Sort by timestamp
        trend_data.sort(key=lambda x: cast(str, x["timestamp"]))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            AtomicFileWriter.write_text(output_path, json.dumps(trend_data, indent=2))
            logger.info(f"Exported active proxy trend data to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export trend data: {e}")
