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
from collections import defaultdict
from collections.abc import Mapping

import httpx

try:  # pragma: no cover - optional dependency handling
    import aiohttp  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover
    aiohttp = cast(Any, None)

from .http_client import get_client
from .etag_cache import load_etags, save_etags
from .security.rate_limiter import RateLimiter

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
    host_semaphores: Dict[str, asyncio.Semaphore] | None = None,
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
        host_semaphores: Optional per-host concurrency semaphores

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
    semaphore = host_semaphores.get(host) if host_semaphores else None

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

    async def _fetch_with_semaphore():
        nonlocal last_error, backoff

        for attempt in range(max_retries):
            try:
                # Start timing the request
                start_time = asyncio.get_event_loop().time()

                logger.debug(f"Attempt {attempt + 1}/{max_retries} for {source} (host: {host})")

                if is_aiohttp_client:
                    async with client.get(source, headers=headers, timeout=timeout) as aio_response:
                        response_time = asyncio.get_event_loop().time() - start_time
                        status_code = aio_response.status
                        response_headers = aio_response.headers
                        http_version = f"{aio_response.version.major}.{aio_response.version.minor}"
                        text = await aio_response.text()
                else:
                    response = await client.get(
                        source,
                        headers=headers,
                        timeout=timeout,
                        follow_redirects=True,
                    )

                    response_time = asyncio.get_event_loop().time() - start_time
                    status_code = response.status_code
                    response_headers = response.headers
                    http_version = getattr(response, "http_version", "1.1")
                    text = response.text

                # Handle 304 Not Modified - cache hit!
                if status_code == 304:
                    logger.info(
                        f"Cache hit (304 Not Modified) for {source} in {response_time:.2f}s"
                    )
                    return FetchResult(
                        source=source,
                        configs=[],
                        success=True,
                        response_time=response_time,
                        status_code=304,
                        error="not-modified",
                    )

                # Check for rate limiting
                if status_code == 429:
                    retry_after_header = _get_header(response_headers, "Retry-After")
                    retry_after_seconds = _parse_retry_after_header(retry_after_header)
                    raise RateLimitError(retry_after_seconds)

                # Check for server errors (5xx)
                if 500 <= status_code < 600:
                    raise FetcherError(f"Server error: {status_code}")

                # Raise for bad status codes
                if status_code >= 400:
                    raise FetcherError(f"HTTP error: {status_code}")

                # Update ETag cache with new validators
                if etag_cache is not None:
                    etag_cache[source] = {}
                    etag_value = _get_header(response_headers, "ETag")
                    if etag_value:
                        etag_cache[source]["etag"] = etag_value
                    last_modified = _get_header(response_headers, "Last-Modified")
                    if last_modified:
                        etag_cache[source]["last_modified"] = last_modified

                # Check content type
                content_type = (_get_header(response_headers, "Content-Type") or "").lower()
                if "html" in content_type and "text/plain" not in content_type:
                    logger.warning(f"Unexpected content type for {source}: {content_type}")

                # Parse configurations
                configs = []
                for line in text.splitlines():
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Basic validation for proxy configs
                    if any(
                        line.startswith(prefix)
                        for prefix in [
                            "vmess://",
                            "vless://",
                            "ss://",
                            "trojan://",
                            "hysteria://",
                            "hysteria2://",
                            "tuic://",
                            "wireguard://",
                            "naive://",
                            "http://",
                            "https://",
                            "socks://",
                            "socks5://",
                            "socks4://",
                        ]
                    ):
                        configs.append(line)
                    else:
                        logger.debug(f"Skipping invalid config line: {line[:50]}...")

                # Log success
                logger.info(
                    f"Successfully fetched {len(configs)} configs from {source} "
                    f"(HTTP/{http_version}, Status: {status_code}, Time: {response_time:.2f}s)"
                )

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

            except asyncio.TimeoutError:
                last_error = f"Timeout after {timeout} seconds"
                logger.warning(
                    "Timeout fetching %s (attempt %d/%d)",
                    source,
                    attempt + 1,
                    max_retries,
                )

            except httpx.TimeoutException:
                last_error = f"Timeout after {timeout} seconds"
                logger.warning(
                    "Timeout fetching %s (attempt %d/%d)",
                    source,
                    attempt + 1,
                    max_retries,
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

            # If not the last attempt, wait before retrying
            if attempt < max_retries - 1:
                delay = min(backoff, 30)
                jitter = random.uniform(0, 0.3)
                logger.debug(
                    "Waiting %.1fs before retrying %s",
                    delay + jitter,
                    source,
                )
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
        try:
            async with semaphore:
                return await _fetch_with_semaphore()  # type: ignore[no-any-return]
        except Exception:
            # Ensure semaphore release on all exceptions
            raise
    else:
        return await _fetch_with_semaphore()  # type: ignore[no-any-return]


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
    sources: list[str], max_concurrent: int = 10, timeout: int = 30, per_host_limit: int = 4
) -> dict[str, FetchResult]:
    """
    Fetch from multiple sources concurrently with HTTP/2, ETag caching, and rate limiting.

    Args:
        sources: List of source URLs
        max_concurrent: Maximum concurrent requests
        timeout: Timeout per request
        per_host_limit: Maximum concurrent requests per host

    Returns:
        Dictionary mapping source URL to FetchResult
    """
    results: Dict[str, FetchResult] = {}

    # Load ETag cache
    etag_cache = load_etags()

    # Create per-host rate limiter (2 requests/second per host by default)
    rate_limiter = RateLimiter(requests_per_second=50.0)

    # Create per-host semaphores for concurrency limiting
    host_semaphores: Dict[str, asyncio.Semaphore] = defaultdict(
        lambda: asyncio.Semaphore(per_host_limit)
    )

    # Create a global semaphore to limit total concurrent requests
    global_semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(client, source):
        async with global_semaphore:
            return await fetch_from_source(
                client,
                source,
                timeout,
                etag_cache=etag_cache,
                rate_limiter=rate_limiter,
                host_semaphores=host_semaphores,
            )

    # Use HTTP/2 client with connection pooling
    async with get_client() as client:
        tasks = [fetch_with_semaphore(client, source) for source in sources]

        # Use asyncio.gather with return_exceptions to handle failures gracefully
        fetch_results: List[FetchResult | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
        )

        for source, result in zip(sources, fetch_results):
            if isinstance(result, BaseException):
                # Handle exceptions that escaped the try-catch
                logger.error(f"Unhandled exception for {source}: {result}")
                results[source] = FetchResult(
                    source=source, configs=[], success=False, error=str(result)
                )
            else:
                results[source] = result

    # Save updated ETag cache
    save_etags(etag_cache)

    # Log summary
    successful = sum(1 for r in results.values() if r.success)
    not_modified = sum(1 for r in results.values() if r.error == "not-modified")
    total_configs = sum(len(r.configs) for r in results.values())
    logger.info(
        f"Fetch complete: {successful}/{len(sources)} sources successful "
        f"({not_modified} not modified), {total_configs} total configs collected"
    )

    return results
