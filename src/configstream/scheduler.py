"""
Intelligent Scheduler.
Prioritizes testing of high-reliability proxies and handles re-test intervals.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from .models import Proxy
from .test_cache import TestResultCache
from .pipeline import PipelineResult

logger = logging.getLogger(__name__)

class SmartRetestScheduler:
    def __init__(self, cache: TestResultCache):
        self.cache = cache
        # Adaptive intervals (in seconds)
        self.intervals = {
            "reliable": 3600,      # 1 hour for good proxies
            "unstable": 600,       # 10 mins for flaky ones
            "dead": 86400,         # 24 hours for dead ones (soft retry)
            "new": 0               # Immediate test
        }

    def filter_proxies_for_retest(self, proxies: List[Proxy]) -> List[Proxy]:
        """
        Filter out proxies that don't need re-testing yet.
        """
        to_test = []
        skipped = 0

        for proxy in proxies:
            if self.should_retest(proxy):
                to_test.append(proxy)
            else:
                skipped += 1

        if skipped > 0:
            logger.info(f"Smart Scheduler: Skipped {skipped} recently tested proxies.")

        return to_test

    def should_retest(self, proxy: Proxy) -> bool:
        """
        Decision engine: Should we test this proxy now?
        """
        cached = self.cache.get(proxy)

        # 1. No history -> Test
        if not cached:
            return True

        # 2. Check timestamp
        if not cached.tested_at:
            return True

        try:
            last_test = datetime.fromisoformat(cached.tested_at)
            now = datetime.now(timezone.utc)
            age = (now - last_test).total_seconds()

            # Determine needed interval based on health
            if cached.is_working:
                # High reliability optimization:
                # If latency is low (< 200ms) and history is good -> extend interval
                required_interval = self.intervals["reliable"]
                if (cached.latency or 999) < 200:
                    required_interval *= 2 # 2 hours
            else:
                # Backoff for dead proxies
                required_interval = self.intervals["dead"]

            return age > required_interval

        except ValueError:
            return True # Corrupt timestamp

    def adjust_pipeline_parameters(self, result: PipelineResult) -> Dict[str, Any]:
        """
        Analyze previous run results to tune next run.
        (Placeholder for future reinforcement learning)
        """
        # Example: If yield was low, increase worker count?
        # Since we don't have a mutable global state for this yet, we return advice.
        advice = {}

        # Fix: PipelineResult is an object, not a dict
        if result.stats.get("working", 0) < 100:
            advice["suggest_more_sources"] = True

        return advice
