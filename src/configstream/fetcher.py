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
from typing import Any, Dict, List
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientTimeout

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
    session: aiohttp.ClientSession,
    source: str,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> FetchResult:
    """
    Fetch proxy configurations from a source with enhanced error handling.

    Args:
        session: aiohttp session for making requests
        source: URL to fetch configurations from
        timeout: Maximum time to wait for response
        max_retries: Number of retry attempts
        retry_delay: Initial delay between retries (exponential backoff)

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

    # Set up timeout configuration
    timeout_config = ClientTimeout(  # type: ignore[call-arg]
        total=timeout,
        connect=timeout / 3,  # Connection timeout is 1/3 of total
        sock_read=timeout / 2,  # Read timeout is 1/2 of total
    )

    # Custom headers to avoid being blocked
    headers = {
        "User-Agent": "ConfigStream/1.0 (github.com/YourUsername/ConfigStream)",
        "Accept": "text/plain, application/json, application/octet-stream, */*",
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    last_error = None
    backoff = retry_delay

    for attempt in range(max_retries):
        try:
            # Start timing the request
            start_time = asyncio.get_event_loop().time()

            logger.debug(f"Attempt {attempt + 1}/{max_retries} for {source}")

            async with session.get(
                source,
                timeout=timeout_config,
                headers=headers,
                allow_redirects=True,
                ssl=True,  # Verify SSL certificates
            ) as response:

                # Calculate response time
                response_time = asyncio.get_event_loop().time() - start_time

                # Check for rate limiting
                if response.status == 429:
                    retry_after_header = response.headers.get("Retry-After")
                    retry_after_seconds = _parse_retry_after_header(retry_after_header)
                    raise RateLimitError(retry_after_seconds)

                # Check for server errors (5xx)
                if 500 <= response.status < 600:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"Server error: {response.status}",
                        headers=response.headers,
                    )

                # Raise for bad status codes
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("Content-Type", "").lower()
                if "html" in content_type and "text/plain" not in content_type:
                    logger.warning(f"Unexpected content type for {source}: {content_type}")

                # Read and process the response
                text = await response.text(encoding="utf-8", errors="ignore")

                # Parse configurations
                configs = []
                for line in text.splitlines():
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Basic validation for proxy configs
                    # (vmess://, vless://, ss://, trojan://, etc.)
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
                    f"(Status: {response.status}, Time: {response_time:.2f}s)"
                )

                return FetchResult(
                    source=source,
                    configs=configs,
                    success=True,
                    response_time=response_time,
                    status_code=response.status,
                )

        except RateLimitError as e:
            delay = e.retry_after if e.retry_after and e.retry_after > 0 else min(backoff, 60)
            jitter = random.uniform(0, 0.5)
            last_error = str(e)
            logger.warning(
                "Rate limit hit for %s; retrying in %.1fs (attempt %d/%d)",
                source,
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

        except aiohttp.ClientError as e:
            last_error = f"HTTP error: {e}"
            logger.warning(f"Client error fetching {source}: {e}")

        except Exception as e:
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
    logger.error(f"Failed to fetch {source} after {max_retries} attempts. Last error: {last_error}")
    return FetchResult(source=source, configs=[], success=False, error=last_error)


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
            if result.success:
                all_configs.extend(result.configs)
        if max_proxies is not None:
            return all_configs[:max_proxies]
        return all_configs


async def fetch_multiple_sources(
    sources: list[str], max_concurrent: int = 10, timeout: int = 30
) -> dict[str, FetchResult]:
    """
    Fetch from multiple sources concurrently with rate limiting.

    Args:
        sources: List of source URLs
        max_concurrent: Maximum concurrent requests
        timeout: Timeout per request

    Returns:
        Dictionary mapping source URL to FetchResult
    """
    results: Dict[str, FetchResult] = {}

    # Create a semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(session, source):
        async with semaphore:
            return await fetch_from_source(session, source, timeout)

    # Create session with connection pooling
    connector = aiohttp.TCPConnector(
        limit=100,  # Total connection pool limit
        limit_per_host=10,  # Per-host connection limit
        ttl_dns_cache=300,  # DNS cache timeout
        enable_cleanup_closed=True,  # Clean up closed connections
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_with_semaphore(session, source) for source in sources]

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

    # Log summary
    successful = sum(1 for r in results.values() if r.success)
    total_configs = sum(len(r.configs) for r in results.values())
    logger.info(
        f"Fetch complete: {successful}/{len(sources)} sources successful, "
        f"{total_configs} total configs collected"
    )

    return results
