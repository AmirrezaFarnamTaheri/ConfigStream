"""
Analytics module for Proxy History.
Calculates stats, trends, and reliability scores.
"""

from typing import Any, Dict, List, Optional


class HistoryAnalytics:
    """Calculates statistics and metrics from history data."""

    @staticmethod
    def get_reliability_score(
        history: Optional[Dict[str, Any]], lookback_days: int = 7
    ) -> float:
        """
        Calculate reliability score based on recent history.
        """
        if not history or "entries" not in history or not history["entries"]:
            return 0.5  # Neutral for unknown

        entries = history["entries"]
        # In a real implementation, we would filter by lookback_days here
        # For now, we use all entries as per original implementation logic
        # (original didn't actually use lookback_days for filtering in the simplified version)

        working_count = sum(1 for e in entries if e["is_working"])
        return working_count / len(entries) if entries else 0.5

    @staticmethod
    def get_trend_data(
        history: Optional[Dict[str, Any]], points: int = 30
    ) -> Dict[str, Any]:
        """Get trend data for charting."""
        if not history or "entries" not in history or not history["entries"]:
            return {"timestamps": [], "latencies": [], "status": []}

        entries = history["entries"][-points:]

        return {
            "timestamps": [e["timestamp"] for e in entries],
            "latencies": [e["latency"] if e["latency"] else 0 for e in entries],
            "status": [1 if e["is_working"] else 0 for e in entries],
        }

    @staticmethod
    def get_history_points(history: Optional[Dict[str, Any]]) -> List[float]:
        """
        Get simplified history (last 10 data points).
        Returns a list of latencies. None/Failures are 9999.
        """
        if not history or "entries" not in history:
            return []

        entries = history["entries"][-10:]
        points = []
        for e in entries:
            if e["is_working"] and e["latency"] is not None:
                points.append(float(e["latency"]))
            else:
                points.append(9999.0)
        return points

    @staticmethod
    def get_summary_stats(history: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary statistics for a proxy."""
        if not history or "entries" not in history or not history["entries"]:
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
            "uptime_percentage": (
                (len(working) / len(entries) * 100) if entries else 0.0
            ),
        }
