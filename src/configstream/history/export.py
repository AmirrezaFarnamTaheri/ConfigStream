# SPDX-License-Identifier: AGPL-3.0-or-later
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
            AtomicFileWriter.write_text(
                output_path, json.dumps(viz_data, indent=2, ensure_ascii=False)
            )
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
                AtomicFileWriter.write_text(
                    output_path, json.dumps([], indent=2, ensure_ascii=False)
                )
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
            AtomicFileWriter.write_text(
                output_path, json.dumps(trend_data, indent=2, ensure_ascii=False)
            )
            logger.info(f"Exported active proxy trend data to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export trend data: {e}")

    @staticmethod
    def export_evasion_trend(
        stats: Dict[str, Any],
        output_path: Path = Path("data/evasion_trend.json"),
        hours_to_track: int = 168,  # 7 days
    ) -> None:
        """
        Exports evasion metrics over time by appending current stats to a time-series file.
        This creates a rolling window of evasion metrics for visualization.
        """
        logger.info("Generating evasion trend data...")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing trend data if available
        existing_data = []
        if output_path.exists():
            try:
                with open(output_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read existing evasion trend data: {e}")
                existing_data = []

        # Extract evasion metrics from stats
        current_timestamp = datetime.now(timezone.utc).isoformat()
        current_entry = {
            "timestamp": current_timestamp,
            "shielded_count": stats.get("shielded_count", 0),
            "revived_warp": stats.get("revived_warp", 0),
            "revived_vwarp": stats.get("revived_vwarp", 0),
            "total_revived": stats.get("total_revived", 0),
            "evasion_utls_enabled": stats.get("evasion_utls_enabled", 0),
            "evasion_alpn_enabled": stats.get("evasion_alpn_enabled", 0),
            "evasion_fragmentation_enabled": stats.get(
                "evasion_fragmentation_enabled", 0
            ),
            "evasion_multiplexing_enabled": stats.get(
                "evasion_multiplexing_enabled", 0
            ),
            "evasion_dns_safe_count": stats.get("evasion_dns_safe_count", 0),
            "evasion_dns_hardened_count": stats.get("evasion_dns_hardened_count", 0),
            "total_valid_proxies": stats.get("total_valid_proxies", 0),
        }

        # Filter out old entries (keep only last N hours)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_to_track)
        filtered_data = []

        for entry in existing_data:
            try:
                ts = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    filtered_data.append(entry)
            except (ValueError, TypeError, KeyError):
                continue

        # Append current entry (avoid duplicates if same timestamp exists)
        # Check if we already have an entry for this timestamp (within 1 minute)
        current_ts = datetime.fromisoformat(current_timestamp.replace("Z", "+00:00"))
        if current_ts.tzinfo is None:
            current_ts = current_ts.replace(tzinfo=timezone.utc)

        # Remove any entry within 1 minute of current timestamp to avoid duplicates
        def get_entry_ts(entry):
            """Helper to parse timestamp from entry."""
            try:
                ts = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                return ts
            except (ValueError, TypeError, KeyError):
                return None

        filtered_data = [
            e
            for e in filtered_data
            if abs((get_entry_ts(e) or current_ts) - current_ts).total_seconds() > 60
        ]

        filtered_data.append(current_entry)

        # Sort by timestamp
        filtered_data.sort(key=lambda x: cast(str, x["timestamp"]))

        try:
            AtomicFileWriter.write_text(
                output_path, json.dumps(filtered_data, indent=2, ensure_ascii=False)
            )
            logger.info(
                f"Exported evasion trend data to {output_path} ({len(filtered_data)} entries)"
            )
        except Exception as e:
            logger.error(f"Failed to export evasion trend data: {e}")
