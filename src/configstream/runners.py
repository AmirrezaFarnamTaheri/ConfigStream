from __future__ import annotations

import asyncio
import logging
from typing import List

from rich.progress import Progress

from .models import Proxy
from .testers import SingBoxTester
from .performance import PerformanceTracker
from .proxy_history import ProxyHistoryTracker
from .smart_scheduler import SmartRetestScheduler
from .test_cache import TestResultCache
from .concurrency_manager import ConcurrencyManager


logger = logging.getLogger(__name__)


class ProxyTestRunner:
    def __init__(
        self,
        progress: Progress | None,
        tracker: PerformanceTracker,
        history_tracker: ProxyHistoryTracker,
        smart_scheduler: SmartRetestScheduler,
        test_cache: TestResultCache,
        tester: SingBoxTester,
        concurrency_manager: ConcurrencyManager,
        batch_size: int,
    ):
        self.progress = progress
        self.tracker = tracker
        self.history_tracker = history_tracker
        self.smart_scheduler = smart_scheduler
        self.test_cache = test_cache
        self.tester = tester
        self.concurrency_manager = concurrency_manager
        self.batch_size = batch_size

    async def run_tests(self, batch: List[Proxy], label: str) -> List[Proxy]:
        if not batch:
            return []

        # Apply smart scheduling to filter proxies needing retest
        original_count = len(batch)
        batch_to_test = self.smart_scheduler.filter_proxies_for_retest(batch)

        # If smart scheduling filtered out all proxies, return cached results
        if not batch_to_test:
            logger.info(
                "All %d proxies in %s have valid cache entries, skipping tests",
                original_count,
                label,
            )
            # Return original proxies, replacing with cached versions when available
            merged = []
            for proxy in batch:
                cached = self.test_cache.get(proxy)
                merged.append(cached if cached else proxy)
            return merged

        # Log smart scheduling efficiency
        if len(batch_to_test) < original_count:
            logger.info(
                "Smart scheduling: testing %d/%d proxies for %s (%.1f%% reduction)",
                len(batch_to_test),
                original_count,
                label,
                (1 - len(batch_to_test) / original_count) * 100,
            )

        task = (
            self.progress.add_task(f"Testing {label}", total=len(batch_to_test))
            if self.progress
            else None
        )

        async def test_single(proxy: Proxy) -> Proxy:
            start_time = asyncio.get_running_loop().time()
            semaphore = self.concurrency_manager.get_semaphore()
            async with semaphore:
                tested_proxy = await self.tester.test(proxy)
            latency = asyncio.get_running_loop().time() - start_time
            self.concurrency_manager.record("default", latency, tested_proxy.is_working)
            self.history_tracker.record_test_result(tested_proxy)
            if self.progress and task is not None:
                self.progress.update(task, advance=1)
            return tested_proxy

        tested: List[Proxy] = []
        total_batches = (len(batch_to_test) + self.batch_size - 1) // self.batch_size
        self.concurrency_manager.start_tuner()
        try:
            with self.tracker.phase("test"):
                for index, start in enumerate(range(0, len(batch_to_test), self.batch_size)):
                    subset = batch_to_test[start : start + self.batch_size]
                    batch_number = index + 1
                    if total_batches > 1:
                        logger.info(
                            "Testing batch %d/%d (%d proxies) for %s",
                            batch_number,
                            total_batches,
                            len(subset),
                            label,
                        )
                    results = await asyncio.gather(*(test_single(p) for p in subset))
                    tested.extend(results)
        finally:
            await self.concurrency_manager.stop_tuner()

        if self.progress and task is not None:
            self.progress.update(task, completed=len(batch_to_test))

        # Merge tested proxies with skipped proxies (preserve order and length)
        if len(tested) < original_count:
            from collections import defaultdict, deque

            def _key(p: Proxy) -> tuple[str, int, str]:
                proto = (p.protocol or "").lower()
                return (p.address, int(p.port), proto)

            buckets: dict[tuple[str, int, str], deque[Proxy]] = defaultdict(deque)
            for p in tested:
                buckets[_key(p)].append(p)

            final_list: List[Proxy] = []
            for proxy in batch:
                k = _key(proxy)
                dq = buckets.get(k)
                if dq and len(dq) > 0:
                    final_list.append(dq.popleft())
                else:
                    cached = self.test_cache.get(proxy)
                    final_list.append(cached if cached else proxy)
            tested = final_list

        return tested
