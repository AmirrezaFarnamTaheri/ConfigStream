# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
from typing import Dict, Optional, Tuple, List
import httpx

from configstream.concurrency_manager import ConcurrencyManager
from configstream.config import AppSettings
from configstream.circuit_breaker import CircuitBreakerManager
from configstream.dns_prewarm import prewarm_dns_cache
from configstream.adaptive_timeout import AdaptiveTimeout
from configstream.http_client import get_client
from configstream.source_quality import SourceQualityTracker
from configstream.fetcher_core.models import FetchResult
from configstream.fetcher_core.orchestrator import fetch_from_source

logger = logging.getLogger(__name__)


async def fetch_multiple_sources(
    sources: List[str],
    max_concurrent: int = 10,
    timeout: int = 30,
    per_host_limit: int = 4,
    client: Optional[httpx.AsyncClient] = None,
    use_adaptive_timeout: bool = True,
    quality_tracker: Optional[SourceQualityTracker] = None,
) -> Dict[str, FetchResult]:
    """
    High-level entry point for batch fetching.
    Orchestrates rate limits, DNS pre-warming, and concurrency.
    """
    results: Dict[str, FetchResult] = {}
    app_settings = AppSettings()

    # Initialize Components
    timeout_tracker = AdaptiveTimeout() if use_adaptive_timeout else None
    rate_limiter = None
    breaker_manager = CircuitBreakerManager(
        failure_threshold=app_settings.CIRCUIT_TRIP_CONN_ERRORS,
        recovery_timeout=app_settings.CIRCUIT_OPEN_SEC,
    )

    # Setup Concurrency Control
    loop = asyncio.get_running_loop()
    controller = ConcurrencyManager(loop, initial_limit=per_host_limit)
    await controller.start_tuner()
    global_sem = asyncio.Semaphore(max_concurrent)

    # Optimization: Pre-warm DNS (Best effort for HTTP sources)
    logger.info(f"Pre-warming DNS for {len(sources)} sources...")
    loop = asyncio.get_running_loop()
    dns_start = loop.time()
    await prewarm_dns_cache(sources)
    dns_dur = float(loop.time() - dns_start)
    logger.info(f"DNS pre-warming completed in {dns_dur:.2f}s.")

    async def _worker(
        http_client: httpx.AsyncClient, source: str
    ) -> Tuple[str, FetchResult]:
        async with global_sem:
            # Use keyword arguments to avoid positional argument mismatch
            # fetch_from_source(client, source, app_settings=...)
            # timeout arg was passed incorrectly as positional app_settings in legacy code
            res = await fetch_from_source(
                http_client,
                source,
                app_settings=app_settings,
                rate_limiter=rate_limiter,
                controller=controller,
                breaker_manager=breaker_manager,
                timeout_tracker=timeout_tracker,
                quality_tracker=quality_tracker,
                # Pass timeout if supported by orchestrator via kwargs or explicit arg?
                # Orchestrator uses timeout_tracker.
            )
            return source, res

    try:
        logger.info(
            f"Starting parallel fetch for {len(sources)} sources (max_concurrent={max_concurrent})"
        )
        start_time = asyncio.get_running_loop().time()
        if client:
            tasks = [_worker(client, s) for s in sources]
            try:
                completed = await asyncio.gather(*tasks)
                for src, res in completed:
                    results[src] = res
            except Exception as e:
                logger.error(f"Error during fetch gather: {e}")
                # Note: If client was passed in, caller is responsible for cleanup
                raise
        else:
            async with get_client() as new_client:
                tasks = [_worker(new_client, s) for s in sources]
                completed = await asyncio.gather(*tasks)
                for src, res in completed:
                    results[src] = res

        duration = asyncio.get_running_loop().time() - start_time
        logger.info(f"Batch fetch completed in {duration:.2f}s")
    finally:
        await controller.stop_tuner()
        if timeout_tracker:
            timeout_tracker.save()

    success_count = sum(1 for r in results.values() if r.success)
    total_bytes = sum(
        len(r.content) for r in results.values() if r.success and r.content
    )
    logger.info(
        f"Fetch Summary: {success_count}/{len(sources)} sources successful. "
        f"Total data fetched: {total_bytes / 1024:.2f} KB"
    )

    return results
