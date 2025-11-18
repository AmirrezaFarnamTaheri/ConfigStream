"""
Intelligent fallback system for serving cached proxies when tests fail.

Provides 100% uptime by serving last known good proxies when current
run fails completely.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

from .models import Proxy

logger = logging.getLogger(__name__)


class FallbackManager:
    """Manages fallback proxy data for high availability."""

    def __init__(self, fallback_path: Path = Path("data/fallback_proxies.json")):
        """
        Initialize fallback manager.

        Args:
            fallback_path: Path to store fallback data
        """
        self.fallback_path = Path(fallback_path)  # Ensure Path object
        self.fallback_path.parent.mkdir(parents=True, exist_ok=True)

    def save_successful_run(
        self,
        proxies: List[Proxy],
        min_count_hard: int = 100,
        min_count_ratio: float = 0.5,
    ) -> None:
        """
        Save successful run for fallback use, but only if it meets quality thresholds.

        Args:
            proxies: List of working proxies from the current successful run.
            min_count_hard: The absolute minimum number of proxies required to save.
            min_count_ratio: The minimum ratio of the new count to the old count.
        """
        new_count = len(proxies)
        if new_count < min_count_hard:
            logger.warning(
                "Fallback NOT saved. Proxy count %d is below hard threshold of %d.",
                new_count,
                min_count_hard,
            )
            return

        # Check against the previous count if a fallback file exists
        if self.fallback_path.exists():
            try:
                data = json.loads(self.fallback_path.read_text())
                previous_count = data.get("proxy_count", 0)
                if new_count < previous_count * min_count_ratio:
                    logger.warning(
                        "Fallback NOT saved. New count %d is less than %.0f%% of previous count %d.",
                        new_count,
                        min_count_ratio * 100,
                        previous_count,
                    )
                    return
            except (json.JSONDecodeError, KeyError):
                logger.warning("Could not read previous fallback count. Saving new data anyway.")

        fallback_data = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "proxy_count": new_count,
            "proxies": [
                {
                    "config": p.config,
                    "protocol": p.protocol,
                    "address": p.address,
                    "port": p.port,
                    "latency": p.latency,
                    "country": p.country,
                    "country_code": p.country_code,
                    "city": p.city,
                }
                for p in proxies[:500]  # Keep top 500 for fallback
            ],
        }

        # Atomic write: write to temp file, then rename
        temp_path = self.fallback_path.with_suffix(".tmp")
        try:
            temp_path.write_text(json.dumps(fallback_data, indent=2))
            temp_path.rename(self.fallback_path)
            logger.info("Successfully saved %d proxies for fallback use.", new_count)
        except OSError as e:
            logger.error("Failed to write fallback file: %s", e)

    def load_fallback(self) -> Optional[List[Proxy]]:
        """
        Load fallback proxies from last successful run.

        Returns:
            List of fallback proxies, or None if not available
        """
        if not self.fallback_path.exists():
            logger.warning("No fallback data available")
            return None

        try:
            data = json.loads(self.fallback_path.read_text())
            proxies = [
                Proxy(
                    config=p["config"],
                    protocol=p["protocol"],
                    address=p["address"],
                    port=p["port"],
                    latency=p.get("latency"),
                    country=p.get("country", ""),
                    country_code=p.get("country_code", ""),
                    city=p.get("city", ""),
                    is_working=True,  # Assume working from last good run
                )
                for p in data["proxies"]
            ]

            logger.info(
                "Loaded %d fallback proxies from %s",
                len(proxies),
                data["saved_at"],
            )
            return proxies

        except Exception as e:
            logger.error("Failed to load fallback data: %s", e)
            return None

    def should_use_fallback(self, current_working_count: int, threshold: int = 10) -> bool:
        """
        Determine if fallback should be used.

        Args:
            current_working_count: Number of working proxies in current run
            threshold: Minimum proxies needed to avoid fallback

        Returns:
            True if fallback should be used
        """
        return current_working_count < threshold
