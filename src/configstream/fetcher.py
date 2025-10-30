"""
Enhanced Fetcher Module with Robust Error Handling
This module provides improved network fetching with retry logic and detailed error reporting
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
from .adaptive_concurrency import AIMDController
from .constants import VALID_PROTOCOLS
from .hedged_requests import hedged_get
from .config import AppSettings
from .circuit_breaker import CircuitBreakerManager
from .dns_prewarm import prewarm_dns_cache
from .metrics_emitter import MetricsEmitter
from pathlib import Path

# Configure structured logging for better debugging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
        configs: list[str],
        success: bool,
        error: str | None = None,
        response_time: float | None = None,
        status_code: int | None = None,
    ):
        self.source = source
        self.configs = configs
        self.success = success
        self.error = error
        self.response_time = response_time
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "source": self.source,
            "config_count": len(self.configs),
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
    controller: AIMDController | None = None,
    breaker_manager: CircuitBreakerManager | None = None,
) -> FetchResult:
    """
    Fetch proxy configurations from a source with enhanced error handling, HTTP/2, and ETag caching.

    Args:
        client: Async HTTP client (httpx.AsyncClient or aiohttp.ClientSession)
        source: URL to fetch configurations from
        timeout: Maximum time to wait for response
        max_retries: Number of retry attempts
        retry_delay: Initial delay between retries (exponential backoff)
        etag_cache: Optional ETag cache dict for conditional GETs
        rate_limiter: Optional per-host rate limiter
        controller: Optional adaptive concurrency controller.

    Returns:
        FetchResult object containing configs and metadata
    """

    # Validate URL format
    try:
        parsed_url = urlparse(source)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid URL format: {source}")
    except Exception as e:
        logger.error(f"URL validation failed for {source}: {e}")
        return FetchResult(source, [], False, error=str(e))

    host = parsed_url.netloc

    # Apply per-host rate limiting
    if rate_limiter:
        while not rate_limiter.is_allowed(host):
            wait_time = rate_limiter.get_wait_time(host)
            logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {host}")
            await asyncio.sleep(wait_time)

    # Apply per-host concurrency limit
    semaphore = controller.get_semaphore(host) if controller else None

    # Check circuit breaker state
    app_settings = AppSettings()
    if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
        breaker = breaker_manager.get_breaker(host)
        if breaker.is_open:
            logger.warning(f"Circuit breaker is open for {host}. Skipping request.")
            return FetchResult(source, [], False, error="Circuit breaker open")

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
            start_time = asyncio.get_event_loop().time()
            success = False
            response_time: float = float(
                timeout
            )  # Default to timeout if exception occurs before assignment
            try:
                logger.debug(f"Attempt {attempt + 1}/{max_retries} for {source} (host: {host})")

                app_settings = AppSettings()
                if app_settings.HEDGING_ENABLED and not is_aiohttp_client:
                    hedge_ms = app_settings.HEDGE_AFTER_MS or 500  # Default to 500ms if None
                    _, response = await hedged_get(
                        client,
                        source,
                        timeout=timeout,
                        hedge_after=float(hedge_ms) / 1000.0,
                        headers=headers,
                    )
                    if not response:
                        raise httpx.RequestError("Hedged request failed")
                elif is_aiohttp_client:
                    aio_response = await client.get(source, headers=headers, timeout=timeout)
                    response = aio_response
                else:
                    response = await client.get(
                        source, headers=headers, timeout=timeout, follow_redirects=True
                    )

                response_time = asyncio.get_event_loop().time() - start_time

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
                        configs=[],
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
                    logger.warning(f"Unexpected content type for {source}: {content_type}")

                configs = []
                for line in text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if any(line.startswith(f"{proto}://") for proto in VALID_PROTOCOLS):
                        configs.append(line)
                    else:
                        logger.debug(f"Skipping invalid config line: {line[:50]}...")
                logger.info(
                    f"Successfully fetched {len(configs)} configs from {source} "
                    f"(HTTP/{http_version}, Status: {status_code}, Time: {response_time:.2f}s)"
                )
                success = True
                return FetchResult(
                    source=source,
                    configs=configs,
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
                logger.warning(f"HTTP error fetching {source}: {e}")
            except httpx.HTTPError as e:
                last_error = f"HTTP error: {e}"
                logger.warning(f"HTTP error fetching {source}: {e}")
            except Exception as e:
                if aiohttp is not None and isinstance(e, aiohttp.ClientError):
                    last_error = f"HTTP error: {e}"
                    logger.warning(f"HTTP error fetching {source}: {e}")
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
        return FetchResult(source=source, configs=[], success=False, error=last_error)

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
        all_configs = []
        for result in results.values():
            if result.success and result.error != "not-modified":
                all_configs.extend(result.configs)
        if max_proxies is not None:
            return all_configs[:max_proxies]
        return all_configs


async def fetch_multiple_sources(
    sources: list[str],
    max_concurrent: int = 10,
    timeout: int = 30,
    per_host_limit: int = 4,
    client: httpx.AsyncClient | None = None,
) -> dict[str, FetchResult]:
    """
    Fetch from multiple sources concurrently with HTTP/2, ETag caching, and rate limiting.

    Args:
        sources: List of source URLs
        max_concurrent: Maximum concurrent requests
        timeout: Timeout per request
        per_host_limit: Maximum concurrent requests per host
        client: Optional httpx.AsyncClient to use for requests.

    Returns:
        Dictionary mapping source URL to FetchResult
    """
    results: Dict[str, FetchResult] = {}

    # Pre-warm DNS cache for top hosts
    await prewarm_dns_cache(sources)

    # Load ETag cache
    etag_cache = load_etags()

    # Create per-host rate limiter (2 requests/second per host by default)
    rate_limiter = RateLimiter(requests_per_second=50.0)

    # Initialize AIMD controller for adaptive concurrency
    loop = asyncio.get_running_loop()
    metrics_emitter = MetricsEmitter(Path("metrics.jsonl"))
    controller = AIMDController(loop, initial_limit=per_host_limit, metrics_emitter=metrics_emitter)
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
            )

    async def _run_tasks(http_client: Any) -> None:
        tasks = [fetch_with_semaphore(http_client, source) for source in sources]
        fetch_results: List[FetchResult | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
        )
        for source, result in zip(sources, fetch_results):
            if isinstance(result, BaseException):
                logger.error(f"Unhandled exception for {source}: {result}")
                results[source] = FetchResult(
                    source=source, configs=[], success=False, error=str(result)
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

    # Write metrics to file
    metrics_emitter.write_metrics()

    # Log summary
    successful = sum(1 for r in results.values() if r.success)
    not_modified = sum(1 for r in results.values() if r.error == "not-modified")
    total_configs = sum(len(r.configs) for r in results.values())
    logger.info(
        f"Fetch complete: {successful}/{len(sources)} sources successful "
        f"({not_modified} not modified), {total_configs} total configs collected"
    )

    return results
