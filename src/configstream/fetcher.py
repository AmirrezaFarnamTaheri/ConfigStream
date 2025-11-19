"""
Enhanced Fetcher Module with Robust Error Handling

This module provides advanced network fetching capabilities including:
- Adaptive timeouts and concurrency control (AIMD)
- Rate limiting and circuit breaker patterns
- ETag/Last-Modified caching
- Hedged requests for improved latency
- Detailed metrics and error reporting
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, cast
from urllib.parse import urlparse
from collections.abc import Mapping

import httpx

try:  # pragma: no cover - optional dependency handling
    import aiohttp
except ModuleNotFoundError:  # pragma: no cover
    aiohttp = cast(Any, None)

from .http_client import get_client
from .etag_cache import load_etags, save_etags
from .security.rate_limiter import RateLimiter
from .concurrency_manager import ConcurrencyManager
from .hedged_requests import hedged_get
from .config import AppSettings
from .circuit_breaker import CircuitBreakerManager
from .dns_prewarm import prewarm_dns_cache
from .adaptive_timeout import AdaptiveTimeout

# Configure structured logging for better debugging
logger = logging.getLogger(__name__)
# Note: Logging level should be controlled globally via configuration,
# not at module import time. Remove the setLevel call to respect global settings.


class FetcherError(Exception):
    """Custom exception for fetcher-related errors"""


class RateLimitError(FetcherError):
    """Raised when rate limiting is detected"""

    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after
        message = (
            f"Rate limited. Retry after {retry_after:.1f} seconds"
            if retry_after is not None
            else "Rate limited. Retry later"
        )
        super().__init__(message)


class FetchResult:
    """Container for fetch results with metadata"""

    def __init__(
        self,
        source: str,
        content: str,
        success: bool,
        error: str | None = None,
        response_time: float | None = None,
        status_code: int | None = None,
    ):
        self.source = source
        self.content = content
        self.success = success
        self.error = error
        self.response_time = response_time
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "source": self.source,
            "content_length": len(self.content),
            "success": self.success,
            "error": self.error,
            "response_time": self.response_time,
            "status_code": self.status_code,
        }


async def fetch_from_source(
    client: Any,
    source: str,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    etag_cache: Dict[str, Dict[str, str]] | None = None,
    rate_limiter: RateLimiter | None = None,
    controller: ConcurrencyManager | None = None,
    breaker_manager: CircuitBreakerManager | None = None,
    timeout_tracker: AdaptiveTimeout | None = None,
) -> FetchResult:
    """
    Fetch proxy configurations from a source with enhanced error handling, HTTP/2, and ETag caching.

    Args:
        client: Async HTTP client (httpx.AsyncClient or aiohttp.ClientSession)
        source: URL to fetch configurations from
        timeout: Maximum time to wait for response (overridden by adaptive timeout if provided)
        max_retries: Number of retry attempts
        retry_delay: Initial delay between retries (exponential backoff)
        etag_cache: Optional ETag cache dict for conditional GETs
        rate_limiter: Optional per-host rate limiter
        controller: Optional adaptive concurrency controller
        breaker_manager: Optional circuit breaker manager
        timeout_tracker: Optional adaptive timeout tracker

    Returns:
        FetchResult object containing configs and metadata
    """

    # Validate URL format
    try:
        parsed_url = urlparse(source)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid URL format: {source}")
    except Exception as e:
        logger.error("URL validation failed for %s: %s", source, e)
        return FetchResult(source, "", False, error=str(e))

    # Normalize baseline timeout
    try:
        base_timeout = int(timeout)
    except Exception:
        logger.warning("Invalid timeout %r for %s, defaulting to 30s", timeout, source)
        base_timeout = 30
    if base_timeout < 5:
        logger.warning("Timeout %ds is too low for %s, using minimum of 5s", base_timeout, source)
        base_timeout = 5

    # Start with caller's normalized baseline
    effective_timeout = base_timeout

    host = parsed_url.netloc

    # Use adaptive timeout if available, but never exceed the caller's baseline budget
    if timeout_tracker:
        adaptive = int(timeout_tracker.get_timeout(source))
        min_allowed = max(5, int(0.5 * base_timeout))  # at least 5s, or half of normalized timeout
        # clamp adaptive to [min_allowed, base_timeout]
        effective_timeout = max(min_allowed, min(adaptive, base_timeout))
    else:
        effective_timeout = base_timeout

    # Use a deadline pattern for timeouts
    deadline = asyncio.get_running_loop().time() + effective_timeout

    # Apply per-host rate limiting
    if rate_limiter:
        while not rate_limiter.is_allowed(host):
            wait_time = rate_limiter.get_wait_time(host)
            logger.debug("Rate limit: waiting %.2fs for %s", wait_time, host)
            await asyncio.sleep(wait_time)

    # Apply per-host concurrency limit
    semaphore = controller.get_semaphore(host) if controller else None

    # Check circuit breaker state
    app_settings = AppSettings()
    if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
        breaker = breaker_manager.get_breaker(host)
        breaker.check_state()
        if breaker.is_open:
            logger.warning("Circuit breaker is open for %s. Skipping request.", host)
            # Do not record synthetic durations for skipped requests to avoid biasing timeouts
            return FetchResult(source, "", False, error="Circuit breaker open")

    # Build headers with optional ETag validators
    headers = {
        "User-Agent": "ConfigStream/1.0 (+https://github.com/AmirrezaFarnamTaheri/ConfigStream)",
        "Accept": "text/plain, application/json, application/octet-stream, */*",
        "Accept-Encoding": "gzip, deflate, br",
    }

    # Add ETag/Last-Modified validators if available
    if etag_cache and source in etag_cache:
        cached = etag_cache[source]
        if "etag" in cached:
            headers["If-None-Match"] = cached["etag"]
        if "last_modified" in cached:
            headers["If-Modified-Since"] = cached["last_modified"]

    last_error = None
    backoff = retry_delay

    def _get_header(headers: Any, name: str) -> str | None:
        if not isinstance(headers, Mapping):
            return None
        for candidate in (name, name.lower(), name.upper()):
            value = headers.get(candidate)
            if value is not None:
                return str(value)
        for key, value in headers.items():
            if isinstance(key, str) and key.lower() == name.lower():
                return str(value)
        return None

    is_aiohttp_client = aiohttp is not None and isinstance(client, aiohttp.ClientSession)

    async def _fetch_with_semaphore() -> FetchResult:
        nonlocal last_error, backoff

        for attempt in range(max_retries):
            loop = asyncio.get_running_loop()
            time_remaining = deadline - loop.time()
            if time_remaining <= 0:
                last_error = "Timeout deadline exceeded"
                logger.warning("Timeout deadline exceeded for %s", source)
                break

            start_time = loop.time()
            success = False
            response_time: float = float(
                time_remaining
            )  # Default to timeout if exception occurs before assignment
            try:
                logger.debug(
                    "Attempt %s/%s for %s (host: %s)", attempt + 1, max_retries, source, host
                )

                app_settings = AppSettings()
                if app_settings.HEDGING_ENABLED and not is_aiohttp_client:
                    hedge_ms = app_settings.HEDGE_AFTER_MS or 500  # Default to 500ms if None
                    _, response = await hedged_get(
                        client,
                        source,
                        timeout=time_remaining,
                        hedge_after=float(hedge_ms) / 1000.0,
                        headers=headers,
                    )
                    if not response:
                        raise httpx.RequestError("Hedged request failed")
                elif is_aiohttp_client:
                    aio_response = await client.get(source, headers=headers, timeout=time_remaining)
                    response = aio_response
                else:
                    response = await client.get(
                        source, headers=headers, timeout=time_remaining, follow_redirects=True
                    )

                response_time = loop.time() - start_time

                if is_aiohttp_client:
                    status_code = response.status
                    response_headers = response.headers
                    http_version = f"{response.version.major}.{response.version.minor}"
                    text = await response.text()
                else:
                    status_code = response.status_code
                    response_headers = response.headers
                    http_version = getattr(response, "http_version", "1.1")
                    text = response.text

                if status_code == 304:
                    logger.info(
                        f"Cache hit (304 Not Modified) for {source} in {response_time:.2f}s"
                    )
                    success = True
                    return FetchResult(
                        source=source,
                        content="",
                        success=True,
                        response_time=response_time,
                        status_code=304,
                        error="not-modified",
                    )

                if status_code == 429:
                    retry_after_header = _get_header(response_headers, "Retry-After")
                    retry_after_seconds = _parse_retry_after_header(retry_after_header)
                    raise RateLimitError(retry_after_seconds)

                if 500 <= status_code < 600:
                    raise FetcherError(f"Server error: {status_code}")
                if status_code >= 400:
                    raise FetcherError(f"HTTP error: {status_code}")

                if etag_cache is not None:
                    etag_cache[source] = {}
                    etag_value = _get_header(response_headers, "ETag")
                    if etag_value:
                        etag_cache[source]["etag"] = etag_value
                    last_modified = _get_header(response_headers, "Last-Modified")
                    if last_modified:
                        etag_cache[source]["last_modified"] = last_modified

                content_type = (_get_header(response_headers, "Content-Type") or "").lower()
                if "html" in content_type and "text/plain" not in content_type:
                    logger.warning("Unexpected content type for %s: %s", source, content_type)

                logger.info(
                    f"Successfully fetched {len(text)} bytes from {source} "
                    f"(HTTP/{http_version}, Status: {status_code}, Time: {response_time:.2f}s)"
                )
                success = True

                # Record successful fetch time for adaptive timeout learning (only on 2xx)
                if timeout_tracker and 200 <= status_code < 300:
                    await timeout_tracker.record(source, response_time)

                return FetchResult(
                    source=source,
                    content=text,
                    success=True,
                    response_time=response_time,
                    status_code=status_code,
                )

            except RateLimitError as e:
                delay = e.retry_after if e.retry_after and e.retry_after > 0 else min(backoff, 60)
                jitter = random.uniform(0, 0.5)
                last_error = str(e)
                logger.warning(
                    "Rate limit hit for %s (host: %s); retrying in %.1fs (attempt %d/%d)",
                    source,
                    host,
                    delay + jitter,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(delay + jitter)
                backoff = min(backoff * 2, 60)
            except (asyncio.TimeoutError, httpx.TimeoutException):
                last_error = f"Timeout after {timeout} seconds"
                logger.warning(
                    "Timeout fetching %s (attempt %d/%d)", source, attempt + 1, max_retries
                )
            except FetcherError as e:
                last_error = str(e)
                logger.warning("HTTP error fetching %s: %s", source, e)
            except httpx.HTTPError as e:
                last_error = f"HTTP error: {e}"
                logger.warning("HTTP error fetching %s: %s", source, e)
            except Exception as e:
                if aiohttp is not None and isinstance(e, aiohttp.ClientError):
                    last_error = f"HTTP error: {e}"
                    logger.warning("HTTP error fetching %s: %s", source, e)
                else:
                    last_error = f"Unexpected error: {e}"
                    logger.error(f"Unexpected error fetching {source}: {e}", exc_info=True)
            finally:
                if controller:
                    final_response_time = asyncio.get_event_loop().time() - start_time
                    controller.record(host, final_response_time, success)
                if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
                    breaker = breaker_manager.get_breaker(host)
                    if success:
                        breaker.record_success()
                    else:
                        breaker.record_failure()

            if attempt < max_retries - 1:
                delay = min(backoff, 30)
                jitter = random.uniform(0, 0.3)
                logger.debug("Waiting %.1fs before retrying %s", delay + jitter, source)
                await asyncio.sleep(delay + jitter)
                backoff = min(backoff * 2, 60)

        # All attempts failed
        logger.error(
            f"Failed to fetch {source} after {max_retries} attempts. Last error: {last_error}"
        )
        return FetchResult(source=source, content="", success=False, error=last_error)

    # Run fetch with optional per-host semaphore
    # Use try/finally to ensure semaphore is released even on error
    if semaphore:
        async with semaphore:
            return await _fetch_with_semaphore()
    else:
        return await _fetch_with_semaphore()


def _parse_retry_after_header(header_value: str | None) -> float | None:
    """Parse an HTTP Retry-After header into seconds."""

    if not header_value:
        return None

    header_value = header_value.strip()
    if not header_value:
        return None

    if header_value.isdigit():
        return float(header_value)

    try:
        parsed = parsedate_to_datetime(header_value)
    except (TypeError, ValueError):
        return None

    if parsed is None:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    now = datetime.now(tz=parsed.tzinfo)
    delta = (parsed - now).total_seconds()
    return max(delta, 0.0)


class SourceFetcher:
    """A class to fetch proxy configurations from multiple sources."""

    async def fetch_all(self, sources: list[str], max_proxies: int | None = None) -> list[str]:
        """
        Fetch all proxy configurations from the given sources.

        Args:
            sources: A list of source URLs.
            max_proxies: The maximum number of proxies to fetch.

        Returns:
            A list of proxy configurations.
        """
        results = await fetch_multiple_sources(sources)
        all_content = []
        for result in results.values():
            if result.success and result.error != "not-modified":
                all_content.append(result.content)

        all_configs = "".join(all_content).splitlines()
        if max_proxies is not None:
            return all_configs[:max_proxies]
        return all_configs


async def fetch_multiple_sources(
    sources: list[str],
    max_concurrent: int = 10,
    timeout: int = 30,
    per_host_limit: int = 4,
    client: httpx.AsyncClient | None = None,
    use_adaptive_timeout: bool = True,
) -> dict[str, FetchResult]:
    """
    Fetch from multiple sources concurrently with HTTP/2, ETag caching, and rate limiting.

    Args:
        sources: List of source URLs
        max_concurrent: Maximum concurrent requests
        timeout: Timeout per request (default, overridden by adaptive if enabled)
        per_host_limit: Maximum concurrent requests per host
        client: Optional httpx.AsyncClient to use for requests
        use_adaptive_timeout: Enable adaptive timeout learning (default: True)

    Returns:
        Dictionary mapping source URL to FetchResult
    """
    results: Dict[str, FetchResult] = {}

    # Initialize adaptive timeout tracker
    timeout_tracker = AdaptiveTimeout() if use_adaptive_timeout else None
    if timeout_tracker:
        await timeout_tracker.initialize()
        stats = timeout_tracker.get_statistics()
        logger.info(
            "Adaptive timeout enabled: %d sources tracked, avg timeout: %.1fs",
            stats["total_sources"],
            stats["avg_timeout"],
        )

    # Pre-warm DNS cache for top hosts
    await prewarm_dns_cache(sources)

    # Load ETag cache
    etag_cache = load_etags()

    # Create per-host rate limiter (2 requests/second per host by default)
    rate_limiter = RateLimiter(requests_per_second=50.0)

    # Initialize AIMD controller for adaptive concurrency
    loop = asyncio.get_running_loop()
    controller = ConcurrencyManager(loop, initial_limit=per_host_limit)
    controller.start_tuner()

    # Initialize Circuit Breaker Manager
    app_settings = AppSettings()
    breaker_manager = CircuitBreakerManager(
        failure_threshold=app_settings.CIRCUIT_TRIP_CONN_ERRORS,
        recovery_timeout=app_settings.CIRCUIT_OPEN_SEC,
    )

    # Create a global semaphore to limit total concurrent requests
    global_semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(http_client: Any, source: str) -> FetchResult:
        async with global_semaphore:
            return await fetch_from_source(
                http_client,
                source,
                timeout,
                etag_cache=etag_cache,
                rate_limiter=rate_limiter,
                controller=controller,
                breaker_manager=breaker_manager,
                timeout_tracker=timeout_tracker,
            )

    async def _run_tasks(http_client: Any) -> None:
        tasks = [fetch_with_semaphore(http_client, source) for source in sources]
        fetch_results: List[FetchResult | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
        )
        for source, result in zip(sources, fetch_results):
            if isinstance(result, BaseException):
                logger.error("Unhandled exception for %s: %s", source, result)
                results[source] = FetchResult(
                    source=source, content="", success=False, error=str(result)
                )
            else:
                results[source] = result

    try:
        if client:
            await _run_tasks(client)
        else:
            async with get_client() as new_client:
                await _run_tasks(new_client)
    finally:
        await controller.stop_tuner()

    # Save updated ETag cache
    save_etags(etag_cache)

    # Log summary
    successful = sum(1 for r in results.values() if r.success)
    not_modified = sum(1 for r in results.values() if r.error == "not-modified")
    total_content_size = sum(len(r.content) for r in results.values())
    logger.info(
        f"Fetch complete: {successful}/{len(sources)} sources successful "
        f"({not_modified} not modified), {total_content_size} total bytes collected"
    )

    return results
