"""
Smart Retest Scheduling System.
Dynamically adjusts proxy retest frequency based on reliability history.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .models import Proxy
from .test_cache import TestResultCache

logger = logging.getLogger(__name__)

class RetestInterval:
    """Tiers for retesting frequency."""
    EXCELLENT = timedelta(hours=12)  # High reliability
    GOOD = timedelta(hours=6)      # Moderate reliability
    FAIR = timedelta(hours=2)      # Flaky
    POOR = timedelta(minutes=30)   # Recently failed (Quick retry)

class SmartRetestScheduler:
    def __init__(self, cache: Optional[TestResultCache] = None):
        self.cache = cache or TestResultCache()

    def should_retest(self, proxy: Proxy) -> bool:
        """
        Decides if a proxy needs retesting.
        """
        # 1. If not in cache, MUST test
        cached = self.cache.get(proxy)
        if not cached:
            return True

        # 2. If previously failed, retest aggressively
        if not cached.is_working:
            return self._check_interval(cached, RetestInterval.POOR)

        # 3. Calculate health-based interval
        # We use a simple heuristic: stable history -> longer interval
        score = self.cache.get_health_score(proxy)

        if score > 0.9:
            interval = RetestInterval.EXCELLENT
        elif score > 0.7:
            interval = RetestInterval.GOOD
        else:
            interval = RetestInterval.FAIR

        return self._check_interval(cached, interval)

    def _check_interval(self, proxy: Proxy, interval: timedelta) -> bool:
        """Returns True if time since last test > interval."""
        if not proxy.tested_at:
            return True

        try:
            # Handle ISO format with potential Z or offsets
            last_test = datetime.fromisoformat(proxy.tested_at.replace('Z', '+00:00'))
            if last_test.tzinfo is None:
                last_test = last_test.replace(tzinfo=timezone.utc)

            age = datetime.now(timezone.utc) - last_test
            return age > interval
        except Exception:
            return True

    def filter_proxies_for_retest(self, proxies: List[Proxy]) -> List[Proxy]:
        """
        Returns only the proxies that need testing.
        """
        to_test = []
        skipped = 0

        for p in proxies:
            if self.should_retest(p):
                to_test.append(p)
            else:
                skipped += 1

        if skipped > 0:
            logger.info("Smart Scheduler: Skipped %d/%d proxies (Healthy)", skipped, len(proxies))

        return to_test

    def get_scheduling_statistics(self) -> dict:
        return self.cache.get_stats()
