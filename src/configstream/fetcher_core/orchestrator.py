# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import random
from urllib.parse import urlparse
from typing import Any, TYPE_CHECKING
import httpx
from configstream.security_validator import SecurityValidator
from configstream.fetcher_core.models import FetchResult
from configstream.config import AppSettings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Use AppSettings if available, otherwise default
try:
    MAX_RESPONSE_SIZE = AppSettings().MAX_RESPONSE_SIZE
except Exception:
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
    **kwargs: Any,  # Accept extra kwargs (controller, quality_tracker) to satisfy Mypy/callers
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
        # Check if it has a valid structure like user/repo/branch/file
        # Often users might copy malformed links.
        # But specifically, the log showed "freevpnspy.raw.githubusercontent.com" which is invalid hostname.
        # This is a specific DNS fix attempt for known pattern if desired, or let DNS fail.
        # Given audit request: "implement a check... to catch obviously malformed hostnames"
        parsed = urlparse(source)
        if parsed.netloc.endswith(".raw.githubusercontent.com"):
            # This implies a subdomain on raw GH, which doesn't exist.
            # e.g. freevpnspy.raw.githubusercontent.com -> likely error
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
        except Exception:
            key = source

        breaker = await breaker_manager.get_breaker(key)

        is_open = breaker.is_open()
        if asyncio.iscoroutine(is_open):
            is_open = await is_open

        if is_open:
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

    headers = {"User-Agent": random.choice(USER_AGENTS)}
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
                    # Log as warning/info and return valid result with empty content
                    # The consumer/parser will handle "no configs found" which is correct behavior.
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
                except Exception:
                    pass
            if breaker:
                try:
                    await breaker.record_failure()
                except Exception:
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
