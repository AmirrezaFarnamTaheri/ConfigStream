import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timezone

from ..config import AppSettings
from ..models import Proxy
from ..test_cache import TestResultCache
from .go import GoBatchTester
from .python import PythonTester

logger = logging.getLogger(__name__)


class SingBoxTester:
    def __init__(
        self,
        timeout: float = 10.0,
        cache: Optional[TestResultCache] = None,
        strict_security: bool = False,
        dry_run: bool = False,
        max_workers: int = 50,
    ):
        self.timeout = timeout
        self.cache = cache
        self.strict_security = strict_security
        self.settings = AppSettings()
        self.dry_run = dry_run
        self.go_tester = GoBatchTester(workers=max_workers)
        self.python_tester = PythonTester(self.settings, timeout, strict_security)

    async def test(self, proxy: Proxy) -> Proxy:
        if self.dry_run:
            proxy.is_working = True
            proxy.latency = 123.45
            proxy.tested_at = datetime.now(timezone.utc).isoformat()
            return proxy

        if self.cache and (cached := self.cache.get(proxy)):
            return cached

        if proxy.protocol.lower() in ("http", "https", "socks", "socks5"):
            return await self.python_tester.test_direct(proxy)

        result = await self.python_tester.test_via_singbox(proxy)
        if self.cache:
            self._finalize_result(result)
        return result

    async def test_batch(self, proxies: List[Proxy]) -> List[Proxy]:
        if self.dry_run:
            for p in proxies:
                p.is_working = True
                p.latency = 123.45
                p.tested_at = datetime.now(timezone.utc).isoformat()
            return proxies

        if self.go_tester.available:
            to_test = []
            for p in proxies:
                if self.cache and (cached := self.cache.get(p)):
                    p.is_working = cached.is_working
                    p.latency = cached.latency
                else:
                    to_test.append(p)

            if to_test:
                await self.go_tester.test_batch(
                    to_test, check_honeypot=self.strict_security
                )
                if self.cache:
                    for p in to_test:
                        self._finalize_result(p)
            return proxies
        else:
            logger.info(
                f"Fallback: Testing batch of {len(proxies)} proxies using Python tester"
            )
            # Cap concurrency to avoid overwhelming the loop/system
            max_concurrent = 100
            sem = asyncio.Semaphore(max_concurrent)

            async def _guarded_test(p: Proxy):
                async with sem:
                    return await self.test(p)

            results = []
            chunk_size = 200
            for i in range(0, len(proxies), chunk_size):
                chunk = proxies[i : i + chunk_size]
                chunk_tasks = [_guarded_test(p) for p in chunk]
                chunk_results = await asyncio.gather(*chunk_tasks)
                results.extend(chunk_results)
            return results

    def _finalize_result(self, proxy: Proxy):
        # proxy.tested_at is set in python_tester methods, or go tester response
        if self.cache:
            # Only cache if we actually got a definitive test result
            # Don't cache if this was never converted/tested properly
            # Check if is_working is False and latency is None - likely a conversion failure
            if not proxy.is_working and proxy.latency is None:
                logger.debug(
                    f"Skipping cache for untested/failed-conversion proxy: {proxy.id}"
                )
                return
            self.cache.set(proxy)

    async def close(self):
        """Clean up resources."""
        if self.go_tester:
            await self.go_tester.close()
