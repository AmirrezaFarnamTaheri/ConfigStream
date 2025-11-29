"""
Production Fetcher Module

This module provides robust network fetching capabilities including:
- Adaptive timeouts and concurrency control (AIMD)
- Rate limiting and circuit breaker patterns
- Hedged requests for improved latency and failover
- Strict error handling for data integrity

NOTE: ETag/304 caching is intentionally disabled to prevent data loss in
stateless execution environments (e.g., GitHub Actions) where the previous
response body is not available.
"""

from __future__ import annotations

import asyncio
import logging
import random
import os
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

from .http_client import get_client
from .security.rate_limiter import RateLimiter
from .concurrency_manager import ConcurrencyManager
from .config import AppSettings
from .circuit_breaker import CircuitBreakerManager
from .dns_prewarm import prewarm_dns_cache
from .adaptive_timeout import AdaptiveTimeout
from .fetcher_core.models import FetchResult, RateLimitError
from .fetcher_core.worker import fetch_single_source

logger = logging.getLogger(__name__)

# Constants
# Allow override via env for low-memory environments
MAX_RESPONSE_SIZE = int(
    os.getenv("MAX_RESPONSE_SIZE", 50 * 1024 * 1024)
)  # Default 50 MB


async def fetch_from_source(
    client: httpx.AsyncClient,
    source: str,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    rate_limiter: Optional[RateLimiter] = None,
    controller: Optional[ConcurrencyManager] = None,
    breaker_manager: Optional[CircuitBreakerManager] = None,
    timeout_tracker: Optional[AdaptiveTimeout] = None,
    app_settings: Optional[AppSettings] = None,
    # Legacy arg kept for compatibility, but unused effectively
    etag_cache: Optional[Dict[str, Dict[str, str]]] = None,
) -> FetchResult:
    """
    Fetch configurations from a source with full resilience logic.
    """
    if app_settings is None:
        app_settings = AppSettings()

    # 1. URL Validation
    try:
        parsed = urlparse(source)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {source}")
        host = parsed.netloc
    except Exception as e:
        return FetchResult(False, source, error=str(e))

    # 2. Adaptive Timeout Calculation
    # We use a strict budget allocation to ensure retries fit within the wall clock
    base_timeout = max(5, int(timeout))
    effective_timeout = base_timeout

    if timeout_tracker:
        adaptive = int(timeout_tracker.get_timeout(source))
        # Clamp between 5s and the user's requested timeout
        effective_timeout = max(5, min(adaptive, base_timeout))

    # Divide budget across attempts, reserving 30% for backoff overhead
    max(1, int(max_retries))
    # Use the full effective timeout for each attempt to handle slow/large sources.
    # We rely on the loop and total wall-clock time (implicit) to manage overall duration.
    per_attempt_timeout = effective_timeout

    # 3. Pre-flight Checks (Rate Limit & Circuit Breaker)
    if rate_limiter:
        while not await rate_limiter.is_allowed(host):
            wait = await rate_limiter.get_wait_time(host)
            await asyncio.sleep(wait)

    if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
        breaker = await breaker_manager.get_breaker(host)
        if await breaker.is_open():
            return FetchResult(False, source, error="Circuit Breaker Open")

    # 4. Execution Loop
    backoff = retry_delay
    last_error = None

    # Standard headers (No ETag to force fresh content)
    headers = {
        "User-Agent": "ConfigStream/1.1",
        "Accept": "text/plain, application/json, */*",
        "Accept-Encoding": "gzip, deflate, br",
    }

    last_status_code = None

    logger.debug(f"Starting fetch for {source} with effective timeout {effective_timeout}s")

    for attempt in range(max_retries):
        loop = asyncio.get_running_loop()
        start_ts = loop.time()

        try:
            logger.debug(f"Fetch attempt {attempt + 1}/{max_retries} for {source}")
            # Delegate to core worker
            result = await fetch_single_source(
                client,
                source,
                headers,
                MAX_RESPONSE_SIZE,
                app_settings,
                per_attempt_timeout,
                start_ts,
                loop,
            )

            # Record metrics on success
            if controller:
                await controller.record(host, float(result.response_time or 0.0), True)
            if timeout_tracker:
                await timeout_tracker.record(source, float(result.response_time or 0.0))
                # Jitter Check
                jitter = await timeout_tracker.get_jitter(source)
                if jitter > 2.0:
                    logger.warning(f"High Jitter detected for {source}: {jitter:.2f}s")

            if result.success:
                logger.info(f"Successfully fetched {len(result.content)} bytes from {source}")
            else:
                 logger.warning(f"Fetch succeeded at network level but returned no valid content/success flag for {source}")

            if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
                breaker = await breaker_manager.get_breaker(host)
                await breaker.record_success()

            return result

        except RateLimitError as e:
            last_error = str(e)
            wait = e.retry_after if e.retry_after else backoff
            await asyncio.sleep(wait + random.uniform(0, 0.5))
            backoff = min(backoff * 2, 60)

        except (httpx.HTTPError, asyncio.TimeoutError, ValueError) as e:
            # Capture status code if available in exception
            if isinstance(e, httpx.HTTPStatusError):
                last_status_code = e.response.status_code
                logger.debug(f"HTTP Error {last_status_code} for {source}")

            last_error = str(e)
            if controller:
                await controller.record(host, float(per_attempt_timeout), False)
            if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
                breaker = await breaker_manager.get_breaker(host)
                await breaker.record_failure()

            # If it's a 4xx/5xx error that was raised, we might want to return it in the result
            # But the loop retries. If we exhaust retries, we return False.
            # However, for 404 specifically, we might want to stop retrying immediately?
            # The current logic retries.
            # If we return a failure FetchResult at the end, it should ideally have the status code of the last attempt.

            # Don't sleep on the last attempt
            if attempt < max_retries - 1:
                wait = min(backoff, 30)
                await asyncio.sleep(wait + random.uniform(0, 0.3))
                backoff = min(backoff * 2, 60)

        except Exception as e:
            logger.exception("Unexpected error fetching %s: %s", source, e)
            last_error = f"Unexpected error: {str(e)}"
            if attempt < max_retries - 1:
                await asyncio.sleep(min(backoff, 30))
                backoff = min(backoff * 2, 60)

    return FetchResult(
        False,
        source,
        error=f"Max retries exceeded: {last_error}",
        status_code=last_status_code,
    )


async def fetch_multiple_sources(
    sources: list[str],
    max_concurrent: int = 10,
    timeout: int = 30,
    per_host_limit: int = 4,
    client: Optional[httpx.AsyncClient] = None,
    use_adaptive_timeout: bool = True,
) -> dict[str, FetchResult]:
    """
    High-level entry point for batch fetching.
    Orchestrates rate limits, DNS pre-warming, and concurrency.
    """
    results: Dict[str, FetchResult] = {}
    app_settings = AppSettings()

    # Initialize Components
    timeout_tracker = AdaptiveTimeout() if use_adaptive_timeout else None
    rate_limiter = RateLimiter(requests_per_second=50.0)
    breaker_manager = CircuitBreakerManager(
        failure_threshold=app_settings.CIRCUIT_TRIP_CONN_ERRORS,
        recovery_timeout=app_settings.CIRCUIT_OPEN_SEC,
    )

    # Setup Concurrency Control
    loop = asyncio.get_running_loop()
    controller = ConcurrencyManager(loop, initial_limit=per_host_limit)
    controller.start_tuner()
    global_sem = asyncio.Semaphore(max_concurrent)

    # Optimization: Pre-warm DNS (Best effort for HTTP sources)
    await prewarm_dns_cache(sources)

    async def _worker(
        http_client: httpx.AsyncClient, source: str
    ) -> Tuple[str, FetchResult]:
        async with global_sem:
            res = await fetch_from_source(
                http_client,
                source,
                timeout,
                rate_limiter=rate_limiter,
                controller=controller,
                breaker_manager=breaker_manager,
                timeout_tracker=timeout_tracker,
                app_settings=app_settings,
            )
            return source, res

    try:
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
    finally:
        await controller.stop_tuner()
        if timeout_tracker:
            timeout_tracker.save()

    success_count = sum(1 for r in results.values() if r.success)
    logger.info(f"Fetch Summary: {success_count}/{len(sources)} sources successful.")

    return results
