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
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

from .http_client import get_client
from .security.rate_limiter import RateLimiter
from .concurrency_manager import ConcurrencyManager
from .hedged_requests import hedged_get
from .config import AppSettings
from .circuit_breaker import CircuitBreakerManager
from .dns_prewarm import prewarm_dns_cache
from .adaptive_timeout import AdaptiveTimeout

logger = logging.getLogger(__name__)


class FetcherError(Exception):
    """Base exception for fetcher-related errors."""


class RateLimitError(FetcherError):
    """Raised when an HTTP 429 Rate Limit is detected."""

    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after
        msg = (
            f"Rate limited. Retry after {retry_after:.1f}s"
            if retry_after
            else "Rate limited."
        )
        super().__init__(msg)


class FetchResult:
    """Container for fetch results with performance metadata."""

    __slots__ = (
        "success",
        "source",
        "content",
        "error",
        "response_time",
        "status_code",
    )

    def __init__(
        self,
        success: bool,
        source: str,
        content: str = "",
        error: str | None = None,
        response_time: float | None = None,
        status_code: int | None = None,
    ):
        self.success = success
        self.source = source
        self.content = content
        self.error = error
        self.response_time = response_time
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "success": self.success,
            "content_length": len(self.content),
            "error": self.error,
            "response_time": self.response_time,
            "status_code": self.status_code,
        }


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
    randomize_tls: bool = False,
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
    attempts = max(1, int(max_retries))
    per_attempt_timeout = max(5, int((effective_timeout * 0.7) / attempts))

    # 3. Pre-flight Checks (Rate Limit & Circuit Breaker)
    if rate_limiter:
        while not rate_limiter.is_allowed(host):
            wait = rate_limiter.get_wait_time(host)
            await asyncio.sleep(wait)

    if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
        breaker = breaker_manager.get_breaker(host)
        if breaker.is_open:
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

    if randomize_tls:
        # Simulate browser-like behavior or fragmentation via headers/order
        # Note: httpx doesn't support true uTLS randomization without custom transport/extensions.
        # We simulate variance by randomizing the accept headers and order
        headers["User-Agent"] = random.choice(
            [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/122.0",
            ]
        )

    for attempt in range(max_retries):
        loop = asyncio.get_running_loop()
        start_ts = loop.time()
        # Removed unused 'success = False'

        try:
            # Execute Request (Standard or Hedged)
            if app_settings.HEDGING_ENABLED:
                hedge_sec = (app_settings.HEDGE_AFTER_MS or 500) / 1000.0
                is_ok, response = await hedged_get(
                    client,
                    source,
                    timeout=per_attempt_timeout,
                    hedge_after=hedge_sec,
                    headers=headers,
                )
                if not is_ok or response is None:
                    # response is the exception in this case
                    raise (
                        response
                        if isinstance(response, Exception)
                        else httpx.RequestError("Hedged request failed")
                    )
            else:
                response = await client.get(
                    source,
                    headers=headers,
                    timeout=per_attempt_timeout,
                    follow_redirects=True,
                )

            response_time = loop.time() - start_ts
            status = response.status_code

            # Rate Limit Handling
            if status == 429:
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                raise RateLimitError(retry_after)

            # Error Handling
            if status >= 400:
                response.raise_for_status()

            # Success
            content = response.text

            # Metric Recording
            if controller:
                controller.record(host, response_time, True)
            if timeout_tracker:
                timeout_tracker.record(source, response_time)
            if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
                breaker_manager.get_breaker(host).record_success()

            return FetchResult(
                True,
                source,
                content=content,
                response_time=response_time,
                status_code=status,
            )

        except RateLimitError as e:
            last_error = str(e)
            wait = e.retry_after if e.retry_after else backoff
            await asyncio.sleep(wait + random.uniform(0, 0.5))
            backoff = min(backoff * 2, 60)

        except (httpx.HTTPError, asyncio.TimeoutError, Exception) as e:
            last_error = str(e)
            if controller:
                controller.record(host, per_attempt_timeout, False)
            if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
                breaker_manager.get_breaker(host).record_failure()

            # Don't sleep on the last attempt
            if attempt < max_retries - 1:
                wait = min(backoff, 30)
                await asyncio.sleep(wait + random.uniform(0, 0.3))
                backoff = min(backoff * 2, 60)

    return FetchResult(False, source, error=f"Max retries exceeded: {last_error}")


def _parse_retry_after(header: str | None) -> float | None:
    """Parse Retry-After header to seconds."""
    if not header:
        return None
    try:
        if header.isdigit():
            return float(header)
        parsed = parsedate_to_datetime(header)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0.0, (parsed - now).total_seconds())
    except Exception:
        return None


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
    Uses as_completed to process results faster (internal optimization),
    though this function currently returns all results at once for compatibility.
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
            # Use gather to execute all
            tasks = [_worker(client, s) for s in sources]
            completed = await asyncio.gather(*tasks)
            for src, res in completed:
                results[src] = res
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
