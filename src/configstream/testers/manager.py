# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import copy
import logging
from typing import List, Optional, Dict
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
        self.max_workers = max_workers
        self.go_tester = GoBatchTester(workers=max_workers, timeout=int(timeout))
        self.python_tester = PythonTester(self.settings, timeout, strict_security)

    async def test(self, proxy: Proxy) -> Proxy:
        if self.dry_run:
            proxy.is_working = True
            proxy.latency = 123.45
            proxy.tested_at = datetime.now(timezone.utc).isoformat()
            return proxy

        if self.cache and (cached := self.cache.get(proxy)):
            return cached

        if proxy.protocol.lower() in ("http", "https", "socks", "socks5", "socks4"):
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
            to_test: List[Proxy] = []
            revived_candidates: List[Proxy] = []

            for p in proxies:
                if p.protocol == "revived" and p.details.get("chain_outbounds"):
                    # Special handling for Revived proxies (chains)
                    revived_candidates.append(p)
                elif self.cache and (cached := self.cache.get(p)):
                    p.is_working = cached.is_working
                    p.latency = cached.latency
                else:
                    to_test.append(p)

            # Test regular proxies
            if to_test:
                await self.go_tester.test_batch(
                    to_test, check_honeypot=self.strict_security
                )
                if self.cache:
                    for p in to_test:
                        self._finalize_result(p)

            # Test revived chains using custom config testing
            if revived_candidates:
                configs = []
                for p in revived_candidates:
                    chain_outbounds = p.details.get("chain_outbounds")
                    if isinstance(chain_outbounds, list):
                        chain_outbounds = copy.deepcopy(chain_outbounds)
                        head_index = None
                        for i, outbound in enumerate(chain_outbounds):
                            if isinstance(outbound, dict) and outbound.get("detour"):
                                head_index = i
                                break
                        if head_index is None:
                            for i, outbound in enumerate(chain_outbounds):
                                if (
                                    isinstance(outbound, dict)
                                    and outbound.get("type") == "wireguard"
                                ):
                                    head_index = i
                                    break
                        if head_index is not None:
                            chain_outbounds[head_index]["tag"] = "proxy"
                            head = chain_outbounds.pop(head_index)
                            chain_outbounds.insert(0, head)
                    configs.append({"id": p.id, "outbounds": chain_outbounds})

                custom_results: Dict[str, bool] = (
                    await self.go_tester.test_custom_configs(
                        configs, check_honeypot=False
                    )
                )
                missing = [p for p in revived_candidates if p.id not in custom_results]
                if missing:
                    logger.warning(
                        "Go tester returned empty/partial results for revived chains; falling back to Python tester."
                    )
                    max_concurrent = max(
                        1, int(self.max_workers) if self.max_workers else 1
                    )
                    sem = asyncio.Semaphore(max_concurrent)

                    async def _fallback_chain_test(p: Proxy) -> Proxy:
                        async with sem:
                            return await self.python_tester.test_via_singbox(p)

                    fallback_results = await asyncio.gather(
                        *[_fallback_chain_test(p) for p in missing]
                    )
                    for res in fallback_results:
                        custom_results[res.id] = bool(res.is_working)

                for p in revived_candidates:
                    is_working = custom_results.get(p.id, False)
                    p.is_working = is_working
                    if is_working:
                        # Use estimated latency instead of fixed 500ms
                        # Mark it as estimated so UI can show it
                        if p.latency is None:
                            p.latency = 200.0  # Optimistic estimate for revived chains
                            p.details["latency_is_estimate"] = True
                    else:
                        p.details["error"] = "REVIVAL_FAILED"

            return proxies
        else:
            logger.info(
                f"Fallback: Testing batch of {len(proxies)} proxies using Python tester"
            )
            max_concurrent = max(1, int(self.max_workers) if self.max_workers else 1)
            sem = asyncio.Semaphore(max_concurrent)

            async def _guarded_test(p: Proxy) -> Proxy:
                async with sem:
                    return await self.test(p)

            results: List[Proxy] = []
            chunk_size = max(1, max_concurrent * 10)
            for i in range(0, len(proxies), chunk_size):
                chunk = proxies[i : i + chunk_size]
                chunk_tasks = [_guarded_test(p) for p in chunk]
                chunk_results = await asyncio.gather(*chunk_tasks)
                results.extend(chunk_results)
            return results

    def _finalize_result(self, proxy: Proxy):
        # proxy.tested_at is set in python_tester methods, or go tester response
        if self.cache:
            # Cache all results including failures to avoid re-testing bad proxies
            # (unless strictly transient failure which we can't distinguish easily yet)
            self.cache.set(proxy)

    async def close(self):
        """Clean up resources."""
        if self.go_tester:
            await self.go_tester.close()
