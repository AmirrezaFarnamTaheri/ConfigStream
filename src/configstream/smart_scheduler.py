"""
Smart Retest Scheduling System
Dynamically adjusts proxy retest frequency based on reliability history.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .models import Proxy
from .test_cache import TestResultCache
from .proxy_history import ProxyHistoryTracker

logger = logging.getLogger(__name__)


class RetestInterval:
    """Retest interval tiers based on proxy reliability."""

    EXCELLENT = timedelta(hours=12)  # >90% uptime
    GOOD = timedelta(hours=6)  # 70-90% uptime
    FAIR = timedelta(hours=4)  # 50-70% uptime
    POOR = timedelta(hours=2)  # <50% uptime


class SmartRetestScheduler:
    """
    Intelligently schedule proxy retests based on historical performance.

    Reduces testing overhead by:
    - Testing reliable proxies less frequently
    - Testing unreliable proxies more frequently
    - Prioritizing recently failed proxies
    """

    def __init__(
        self,
        cache: Optional[TestResultCache] = None,
        history: Optional[ProxyHistoryTracker] = None,
    ):
        """
        Initialize smart scheduler.

        Args:
            cache: Test result cache (created if not provided)
            history: Proxy history tracker (created if not provided)
        """
        self.cache = cache or TestResultCache()
        self.history = history or ProxyHistoryTracker()

    def should_retest(self, proxy: Proxy) -> bool:
        """
        Determine if a proxy should be retested based on its history.

        Args:
            proxy: Proxy to evaluate

        Returns:
            True if proxy should be retested, False otherwise
        """
        # Check cache for recent test
        cached_proxy = self.cache.get(proxy)

        if cached_proxy is None:
            # No cache entry or expired - always retest
            logger.debug(
                "Retest needed for %s:%s (no valid cache entry)", proxy.address, proxy.port
            )
            return True

        # Get health score from historical data
        health_score = self.cache.get_health_score(proxy)

        # Calculate appropriate retest interval
        interval = self._get_retest_interval(health_score)

        # Check when last tested
        last_test_time = self._get_last_test_time(cached_proxy)

        if last_test_time is None:
            logger.debug("Retest needed for %s:%s (no timestamp)", proxy.address, proxy.port)
            return True

        time_since_test = datetime.now(timezone.utc) - last_test_time
        should_retest = time_since_test >= interval

        if should_retest:
            logger.debug(
                "Retest needed for %s:%s (health: %.2f, last: %.1fh ago, interval: %.1fh)",
                proxy.address,
                proxy.port,
                health_score,
                time_since_test.total_seconds() / 3600,
                interval.total_seconds() / 3600,
            )
        else:
            logger.debug(
                "Retest skipped for %s:%s (health: %.2f, tested %.1fh ago)",
                proxy.address,
                proxy.port,
                health_score,
                time_since_test.total_seconds() / 3600,
            )

        return should_retest

    def _get_retest_interval(self, health_score: float) -> timedelta:
        """
        Get appropriate retest interval based on health score.

        Args:
            health_score: Health score (0.0 - 1.0)

        Returns:
            Retest interval timedelta
        """
        if health_score >= 0.9:
            return RetestInterval.EXCELLENT
        elif health_score >= 0.7:
            return RetestInterval.GOOD
        elif health_score >= 0.5:
            return RetestInterval.FAIR
        else:
            return RetestInterval.POOR

    def _get_last_test_time(self, proxy: Proxy) -> Optional[datetime]:
        """
        Extract last test time from proxy.

        Args:
            proxy: Proxy with test results

        Returns:
            Last test datetime or None
        """
        if not proxy.tested_at:
            return None

        try:
            # Parse ISO format timestamp
            return datetime.fromisoformat(proxy.tested_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            logger.warning("Failed to parse timestamp for %s:%s: %s", proxy.address, proxy.port, e)
            return None

    def filter_proxies_for_retest(self, proxies: List[Proxy]) -> List[Proxy]:
        """
        Filter proxy list to only include those needing retest.

        Args:
            proxies: List of proxies to evaluate

        Returns:
            Filtered list of proxies that need retesting
        """
        retest_needed = []
        skipped = 0

        for proxy in proxies:
            if self.should_retest(proxy):
                retest_needed.append(proxy)
            else:
                skipped += 1

        reduction_pct = (skipped / len(proxies) * 100) if proxies else 0

        logger.info(
            "Smart scheduling: %d proxies need retest, %d skipped (%.1f%% reduction)",
            len(retest_needed),
            skipped,
            reduction_pct,
        )

        return retest_needed

    def get_scheduling_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about scheduling decisions.

        Returns:
            Dictionary with scheduling stats
        """
        cache_stats = self.cache.get_stats()

        # This would require iterating through all proxies
        # For now, return cache stats
        return {
            "cache_valid_entries": cache_stats["valid_entries"],
            "cache_expired_entries": cache_stats["expired_entries"],
            "average_health_score": cache_stats["average_health_score"],
            "ttl_seconds": cache_stats["ttl_seconds"],
            "intervals": {
                "excellent": RetestInterval.EXCELLENT.total_seconds() / 3600,
                "good": RetestInterval.GOOD.total_seconds() / 3600,
                "fair": RetestInterval.FAIR.total_seconds() / 3600,
                "poor": RetestInterval.POOR.total_seconds() / 3600,
            },
        }

    def force_retest_failed(self, proxies: List[Proxy]) -> List[Proxy]:
        """
        Mark failed proxies for immediate retest.

        Args:
            proxies: List of proxies

        Returns:
            List with failed proxies prioritized
        """
        failed = []
        working = []

        for proxy in proxies:
            if not proxy.is_working:
                failed.append(proxy)
            else:
                working.append(proxy)

        # Failed proxies first (they need quick revalidation)
        # Then working proxies (can use smart scheduling)
        result = failed + working

        if failed:
            logger.info("Prioritizing %d failed proxies for immediate retest", len(failed))

        return result

    def get_next_retest_time(self, proxy: Proxy) -> Optional[datetime]:
        """
        Calculate when a proxy should next be retested.

        Args:
            proxy: Proxy to evaluate

        Returns:
            Next retest datetime, or None if immediate retest needed
        """
        cached_proxy = self.cache.get(proxy)

        if cached_proxy is None:
            return None  # Immediate retest needed

        health_score = self.cache.get_health_score(proxy)
        interval = self._get_retest_interval(health_score)
        last_test_time = self._get_last_test_time(cached_proxy)

        if last_test_time is None:
            return None  # Immediate retest needed

        return last_test_time + interval


# Global scheduler instance
_global_scheduler: Optional[SmartRetestScheduler] = None


def get_scheduler() -> SmartRetestScheduler:
    """Get or create the global scheduler instance."""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = SmartRetestScheduler()
    return _global_scheduler


def should_retest_proxy(proxy: Proxy) -> bool:
    """
    Convenience function to check if a proxy should be retested.

    Args:
        proxy: Proxy to evaluate

    Returns:
        True if retest needed
    """
    scheduler = get_scheduler()
    return scheduler.should_retest(proxy)
