# SPDX-License-Identifier: AGPL-3.0-or-later
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
    GOOD = timedelta(hours=6)  # Moderate reliability
    FAIR = timedelta(hours=2)  # Flaky
    POOR = timedelta(minutes=30)  # Recently failed (Quick retry)


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

        should = self._check_interval(cached, interval)
        if not should:
            # Log debug info about skip reason
            logger.debug(
                f"Skipping retest for {proxy.id[:8]} (Score: {score:.2f}). "
                f"Next test allowed in {interval}"
            )
        return should

    def _check_interval(self, proxy: Proxy, interval: timedelta) -> bool:
        """Returns True if time since last test > interval."""
        if not proxy.tested_at:
            return True

        try:
            # Handle ISO format with potential Z or offsets
            last_test = datetime.fromisoformat(proxy.tested_at.replace("Z", "+00:00"))
            if last_test.tzinfo is None:
                last_test = last_test.replace(tzinfo=timezone.utc)

            age = datetime.now(timezone.utc) - last_test
            should_retest = age > interval
            if should_retest:
                logger.debug(
                    f"Retesting {proxy.id[:8]}: Age {age} > Interval {interval}"
                )
            return should_retest
        except Exception as e:
            logger.warning(f"Error parsing date for {proxy.id[:8]}: {e}")
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
            logger.info(
                f"Smart Scheduler: Skipped {skipped}/{len(proxies)} proxies (Healthy)"
            )

        return to_test

    def get_scheduling_statistics(self) -> dict:
        return self.cache.get_stats()
