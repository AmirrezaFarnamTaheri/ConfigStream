# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import random
from urllib.parse import urlparse
from typing import Any, Dict, Optional, Tuple, List
import httpx

from configstream.concurrency_manager import ConcurrencyManager
from configstream.config import AppSettings
from configstream.circuit_breaker import CircuitBreakerManager
from configstream.dns_cache import prewarm_dns_cache
from configstream.adaptive_timeout import AdaptiveTimeout
from configstream.http_client import get_client
from configstream.source_quality import SourceQualityTracker
from configstream.security_validator import SecurityValidator
from configstream.fetcher_worker import FetchResult

logger = logging.getLogger(__name__)

# Use AppSettings if available, otherwise default
try:
    MAX_RESPONSE_SIZE = AppSettings().MAX_RESPONSE_SIZE
except Exception:  # nosec
    MAX_RESPONSE_SIZE = 10 * 1024 * 1024

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
]


async def fetch_from_source(
    client: httpx.AsyncClient,
    source: str,
    app_settings: Any = None,
    max_retries: int = 3,
    rate_limiter: Any = None,
    breaker_manager: Any = None,
    timeout_tracker: Any = None,
    retry_delay: float = 1.0,
    timeout: float | None = None,
    **kwargs: Any,  # Accept extra kwargs to satisfy Mypy/callers
) -> Any:
    """
    Robust fetcher implementation handling retries, circuit breaking, rate limiting,
    and response size limits.
    """

    loop = asyncio.get_running_loop()
    safe_source = SecurityValidator.sanitize_log_message(source)

    # Validate URL
    if not source or not source.startswith(("http://", "https://")):
        return FetchResult(
            success=False, source=source, content="", error="Invalid URL", status_code=0
        )

    # Sanitize malformed raw.githubusercontent URLs
    if "raw.githubusercontent" in source and "github.com" not in source:
        parsed = urlparse(source)
        if parsed.netloc.endswith(".raw.githubusercontent.com"):
            return FetchResult(
                success=False,
                source=source,
                content="",
                error="Malformed GitHub URL",
                status_code=0,
            )

    # Circuit Breaker Check
    breaker = None
    if breaker_manager:
        try:
            parsed = urlparse(source)
            host = parsed.netloc
            key = host
        except Exception:  # nosec
            key = source

        breaker = await breaker_manager.get_breaker(key)

        is_open = breaker.is_open()
        if asyncio.iscoroutine(is_open):
            is_open = await is_open

        if is_open:
            should_log_open = False
            should_log_fn = getattr(breaker, "should_log_open", None)
            if callable(should_log_fn):
                maybe_should_log = should_log_fn()
                if asyncio.iscoroutine(maybe_should_log):
                    should_log_open = await maybe_should_log
                else:
                    should_log_open = bool(maybe_should_log)
            if should_log_open:
                logger.warning(
                    "Circuit breaker opened for host %s; skipping fetches temporarily.",
                    SecurityValidator.sanitize_log_message(str(key)),
                )
            return FetchResult(
                success=False,
                source=source,
                content="",
                error="Circuit Breaker Open",
                status_code=0,
            )

    # Rate Limiter Pre-check
    if rate_limiter:
        if not await rate_limiter.is_allowed(source):
            wait_time = await rate_limiter.get_wait_time(source)
            if wait_time > 0:
                await asyncio.sleep(wait_time)

    headers = {"User-Agent": random.choice(USER_AGENTS)}  # nosec
    attempt = 0
    last_error = None

    # Use instance limit if passed, else global default
    max_size_raw = app_settings.MAX_RESPONSE_SIZE if app_settings else MAX_RESPONSE_SIZE
    try:
        max_size = int(max_size_raw)
    except (TypeError, ValueError):
        max_size = 0

    while attempt < max_retries:
        start_ts = loop.time()
        try:
            # Jitter / Timeout Tracking
            effective_timeout = float(timeout) if timeout is not None else 30.0
            if timeout_tracker:
                adaptive_timeout = timeout_tracker.get_timeout(source)
                if timeout is not None:
                    adaptive_timeout = min(adaptive_timeout, float(timeout))
                effective_timeout = adaptive_timeout
                jitter = await timeout_tracker.get_jitter(source)
                if jitter > 2.0:
                    logger.info(f"High Jitter detected for {safe_source}: {jitter}s")

            async with client.stream(
                "GET",
                source,
                headers=headers,
                timeout=effective_timeout,
                follow_redirects=True,
            ) as response:

                # Check Status
                if response.status_code == 429:
                    response_time = loop.time() - start_ts
                    if timeout_tracker:
                        await timeout_tracker.record_attempt(
                            source, response_time, success=False
                        )
                    if breaker:
                        await breaker.record_failure()
                    retry_after = response.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else 2.0
                    await asyncio.sleep(wait)
                    attempt += 1
                    last_error = "Rate limited"
                    continue

                if response.status_code in [404, 410]:
                    response_time = loop.time() - start_ts
                    if timeout_tracker:
                        await timeout_tracker.record_attempt(
                            source, response_time, success=False
                        )
                    if breaker:
                        await breaker.record_failure()
                    return FetchResult(
                        success=False,
                        source=source,
                        content="",
                        error=f"Permanent Error: {response.status_code}",
                        status_code=response.status_code,
                        response_time=response_time,
                    )

                if response.status_code >= 500:
                    response_time = loop.time() - start_ts
                    if timeout_tracker:
                        await timeout_tracker.record_attempt(
                            source, response_time, success=False
                        )
                    if breaker:
                        await breaker.record_failure()
                    attempt += 1
                    last_error = f"HTTP {response.status_code}"
                    await asyncio.sleep(retry_delay * (2**attempt))
                    continue

                if response.status_code >= 400:
                    response_time = loop.time() - start_ts
                    if timeout_tracker:
                        await timeout_tracker.record_attempt(
                            source, response_time, success=False
                        )
                    if breaker:
                        await breaker.record_failure()
                    return FetchResult(
                        success=False,
                        source=source,
                        content="",
                        error=f"HTTP {response.status_code}",
                        status_code=response.status_code,
                        response_time=response_time,
                    )

                # Content Length Check
                content_len = response.headers.get("Content-Length")
                content_len_int = None
                if content_len:
                    try:
                        content_len_int = int(content_len)
                    except (TypeError, ValueError):
                        content_len_int = None
                if max_size > 0 and content_len_int and content_len_int > max_size:
                    response_time = loop.time() - start_ts
                    if timeout_tracker:
                        await timeout_tracker.record_attempt(
                            source, response_time, success=False
                        )
                    if breaker:
                        await breaker.record_failure()
                    return FetchResult(
                        success=False,
                        source=source,
                        content="",
                        error="Response too large",
                        status_code=response.status_code,
                        response_time=response_time,
                    )

                # Stream Content
                content_parts = []
                current_size = 0
                async for chunk in response.aiter_bytes():
                    current_size += len(chunk)
                    if max_size > 0 and current_size > max_size:
                        response_time = loop.time() - start_ts
                        if timeout_tracker:
                            await timeout_tracker.record_attempt(
                                source, response_time, success=False
                            )
                        if breaker:
                            await breaker.record_failure()
                        return FetchResult(
                            success=False,
                            source=source,
                            content="",
                            error="Response too large",
                            status_code=response.status_code,
                            response_time=response_time,
                        )
                    content_parts.append(chunk)

                content = b"".join(content_parts)

                # Decode
                text_content = content.decode("utf-8", errors="ignore")

                # Handle empty 200 OK responses gracefully
                if response.status_code == 200 and (
                    not text_content or not text_content.strip()
                ):
                    logger.info(
                        f"Source {safe_source} returned 200 OK but empty content."
                    )
                    response_time = loop.time() - start_ts
                    if timeout_tracker:
                        await timeout_tracker.record_attempt(
                            source, response_time, success=True
                        )
                    if breaker:
                        await breaker.record_success()
                    return FetchResult(
                        success=True,  # Valid HTTP transaction
                        source=source,
                        content="",  # Empty
                        status_code=200,
                        error="Empty content",  # Informative, not exception
                        response_time=response_time,
                    )

                response_time = loop.time() - start_ts
                if timeout_tracker:
                    await timeout_tracker.record_attempt(
                        source, response_time, success=True
                    )
                if breaker:
                    await breaker.record_success()
                return FetchResult(
                    success=True,
                    source=source,
                    content=text_content,
                    status_code=response.status_code,
                    error=None,
                    response_time=response_time,
                )

        except asyncio.CancelledError:
            logger.warning(f"Fetch for {safe_source} cancelled by outer signal.")
            # Propagate cancellation to abort fetch immediately
            raise
        except Exception as e:
            last_error = str(e)
            if timeout_tracker:
                try:
                    await timeout_tracker.record_attempt(
                        source, loop.time() - start_ts, success=False
                    )
                except Exception:  # nosec
                    pass
            if breaker:
                try:
                    await breaker.record_failure()
                except Exception:  # nosec
                    pass
            attempt += 1
            await asyncio.sleep(retry_delay)

    return FetchResult(
        success=False,
        source=source,
        content="",
        error=f"Max retries exceeded: {last_error}",
        status_code=0,
    )


async def fetch_multiple_sources(
    sources: List[str],
    max_concurrent: int = 10,
    timeout: int = 30,
    per_host_limit: int = 4,
    client: Optional[httpx.AsyncClient] = None,
    use_adaptive_timeout: bool = True,
    quality_tracker: Optional[SourceQualityTracker] = None,
    breaker_manager: Optional[CircuitBreakerManager] = None,
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
    if breaker_manager is None:
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
            # Use keyword arguments for clarity
            res = await fetch_from_source(
                http_client,
                source,
                app_settings=app_settings,
                rate_limiter=rate_limiter,
                controller=controller,
                breaker_manager=breaker_manager,
                timeout_tracker=timeout_tracker,
                quality_tracker=quality_tracker,
                timeout=timeout,
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
