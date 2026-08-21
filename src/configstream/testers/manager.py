# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import copy
import logging
from typing import TYPE_CHECKING, Dict, List, Optional
from datetime import datetime, timezone

from ..config import AppSettings
from ..models import Proxy
from ..test_cache import TestResultCache
from ..converters.chain_outbounds import chain_outbounds_from_details
from .go import GoBatchTester

if TYPE_CHECKING:
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
        self._python_tester: Optional["PythonTester"] = None

    @property
    def python_tester(self) -> "PythonTester":
        """Create the optional Python fallback only when a code path needs it.

        Core pipeline imports and dry-run execution must not require the
        ``aiohttp-socks`` dependency used solely by the Python proxy fallback.
        """
        if self._python_tester is None:
            from .python import PythonTester

            self._python_tester = PythonTester(
                self.settings, self.timeout, self.strict_security
            )
        return self._python_tester

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

    async def _test_python_batch(self, proxies: List[Proxy]) -> List[Proxy]:
        """Test a batch through the Python fallback with bounded concurrency."""
        max_concurrent = max(1, int(self.max_workers) if self.max_workers else 1)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def guarded_test(proxy: Proxy) -> Proxy:
            async with semaphore:
                return await self.test(proxy)

        results: List[Proxy] = []
        chunk_size = max_concurrent * 10
        for index in range(0, len(proxies), chunk_size):
            chunk = proxies[index : index + chunk_size]
            results.extend(
                await asyncio.gather(*(guarded_test(proxy) for proxy in chunk))
            )
        return results

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
                if p.protocol == "revived" and chain_outbounds_from_details(
                    p.details or {}
                ):
                    # Special handling for Revived proxies (chains)
                    revived_candidates.append(p)
                elif self.cache and (cached := self.cache.get(p)):
                    p.is_working = cached.is_working
                    p.latency = cached.latency
                else:
                    to_test.append(p)

            # Test regular proxies
            if to_test:
                try:
                    await self.go_tester.test_batch(
                        to_test, check_honeypot=self.strict_security
                    )
                    if self.cache:
                        for p in to_test:
                            self._finalize_result(p)
                except Exception as e:
                    logger.warning(
                        f"Go Tester failed for batch ({len(to_test)} proxies): {e}. Falling back to Python."
                    )
                    await self._test_python_batch(to_test)
                    # Proxies updated in place via list reference

            # Test revived chains using custom config testing
            if revived_candidates:
                configs = []
                for p in revived_candidates:
                    chain_outbounds = copy.deepcopy(
                        chain_outbounds_from_details(p.details or {})
                    )
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

                try:
                    custom_results: Dict[str, bool] = (
                        await _run_revived_custom_go(
                            self, configs
                        )
                    )
                except Exception as e:
                    logger.warning(
                        f"Go Tester failed for revived chains: {e}. Falling back."
                    )
                    custom_results = {}
                missing = [p for p in revived_candidates if p.id not in custom_results]
                _record_revived_go_health(self, len(missing))
                if missing:
                    custom_results.update(
                        await _bounded_revived_python_fallback(self, missing)
                    )

                for p in revived_candidates:
                    is_working = custom_results.get(p.id, False)
                    p.is_working = is_working
                    p.tested_at = datetime.now(timezone.utc).isoformat()
                    if is_working:
                        # Use estimated latency instead of fixed 500ms
                        # Mark it as estimated so UI can show it
                        if p.latency is None:
                            p.latency = 200.0  # Optimistic estimate for revived chains
                            p.details["latency_is_estimate"] = True
                    else:
                        p.details.setdefault("error", "REVIVAL_FAILED")

            return proxies
        else:
            logger.info(
                f"Fallback: Testing batch of {len(proxies)} proxies using Python tester"
            )
            return await self._test_python_batch(proxies)

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


async def _run_revived_custom_go(
    tester: SingBoxTester, configs: List[Dict[str, object]]
) -> Dict[str, bool]:
    """Run custom Go chain tests under a lifecycle circuit breaker and deadline."""

    if bool(getattr(tester, "_revived_go_disabled", False)):
        logger.warning(
            "Go custom-config testing is disabled after repeated incomplete results; "
            "using bounded Python fallback for revived chains."
        )
        return {}
    try:
        return await asyncio.wait_for(
            tester.go_tester.test_custom_configs(configs, check_honeypot=False),
            timeout=max(30.0, float(tester.timeout) * 2.0),
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Go Tester timed out for revived chains; falling back within the bounded recovery budget."
        )
        return {}


def _record_revived_go_health(tester: SingBoxTester, missing_count: int) -> None:
    """Trip the custom-config path after five consecutive incomplete results."""

    if bool(getattr(tester, "_revived_go_disabled", False)):
        return
    if missing_count <= 0:
        setattr(tester, "_revived_go_failures", 0)
        return
    failures = int(getattr(tester, "_revived_go_failures", 0)) + 1
    limit = int(getattr(tester, "_revived_go_failure_limit", 5))
    setattr(tester, "_revived_go_failures", failures)
    if failures >= limit:
        setattr(tester, "_revived_go_disabled", True)
        logger.error(
            "Go custom-config testing reached the five-strike incomplete-result limit; "
            "disabling that path for the rest of this tester lifecycle."
        )


async def _bounded_revived_python_fallback(
    tester: SingBoxTester, missing: List[Proxy]
) -> Dict[str, bool]:
    """Bound revived-chain Python recovery by count, concurrency, and wall time."""

    fallback_limit = max(1, int(tester.settings.PY_TESTER_BATCH_SIZE))
    fallback_candidates = missing[:fallback_limit]
    skipped_candidates = missing[fallback_limit:]
    logger.warning(
        "Go tester returned empty/partial results for revived chains; "
        "testing at most %d candidates with the Python fallback.",
        fallback_limit,
    )
    max_concurrent = max(1, int(tester.max_workers) if tester.max_workers else 1)
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fallback_chain_test(proxy: Proxy) -> Proxy:
        async with semaphore:
            return await tester.python_tester.test_via_singbox(proxy)

    try:
        raw_results = await asyncio.wait_for(
            asyncio.gather(
                *(fallback_chain_test(proxy) for proxy in fallback_candidates),
                return_exceptions=True,
            ),
            timeout=max(30.0, float(tester.timeout) * 2.0),
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Python revived-chain fallback exceeded its bounded recovery deadline."
        )
        raw_results = []

    results: Dict[str, bool] = {}
    for result in raw_results:
        if isinstance(result, Proxy):
            results[result.id] = bool(result.is_working)

    skipped_at = datetime.now(timezone.utc).isoformat()
    for proxy in skipped_candidates:
        proxy.is_working = False
        proxy.tested_at = skipped_at
        proxy.details["error"] = "REVIVAL_FALLBACK_BUDGET_EXHAUSTED"
        proxy.details["failure_category"] = "INFRA_BUDGET"
    return results
