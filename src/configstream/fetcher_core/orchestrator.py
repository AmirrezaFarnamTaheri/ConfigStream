import asyncio
import logging
import random
from typing import Dict, Optional
from urllib.parse import urlparse
import httpx

from ..security.rate_limiter import RateLimiter
from ..concurrency_manager import ConcurrencyManager
from ..config import AppSettings
from ..circuit_breaker import CircuitBreakerManager
from ..adaptive_timeout import AdaptiveTimeout
from .models import FetchResult, RateLimitError
from .worker import fetch_single_source
from ..security_validator import SecurityValidator
from .constants import MAX_RESPONSE_SIZE

logger = logging.getLogger(__name__)

# Browser User-Agent pool for rotation
# These mimic common browsers to avoid fingerprinting and blocking
USER_AGENT_POOL = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

# HTTP status codes that indicate server issues (should trip breaker)
SERVER_ERROR_CODES = {500, 502, 503, 504, 520, 521, 522, 523, 524, 525, 526}

# HTTP status codes that indicate client/resource issues (should NOT trip breaker)
CLIENT_ERROR_CODES = {400, 401, 403, 404, 405, 410, 429}


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
    sanitized_source = SecurityValidator.sanitize_log_message(source)
    try:
        parsed = urlparse(source)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {sanitized_source}")
        host = parsed.netloc
    except Exception as e:
        logger.debug(f"URL validation failed for {sanitized_source}: {e}")
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
    max_retries = max(1, int(max_retries))
    # Use the full effective timeout for each attempt to handle slow/large sources.
    # We rely on the loop and total wall-clock time (implicit) to manage overall duration.
    per_attempt_timeout = effective_timeout

    # 3. Pre-flight Checks (Rate Limit & Circuit Breaker)
    if rate_limiter:
        while not await rate_limiter.is_allowed(host):
            wait = await rate_limiter.get_wait_time(host)
            logger.debug(f"Rate limiting active for {host}. Waiting {wait:.2f}s...")
            await asyncio.sleep(wait)

    if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
        breaker = await breaker_manager.get_breaker(host)
        if await breaker.is_open():
            # Only log warning if it's the first time we noticed it's open (debounce)
            # or simply use debug to avoid spam
            logger.debug(
                f"Circuit Breaker BLOCKED request to {host} (Source: {source}). "
            )
            return FetchResult(False, source, error="Circuit Breaker Open")

    # 4. Execution Loop
    backoff = retry_delay
    last_error = None

    # Standard headers with rotating User-Agent
    headers = {
        "User-Agent": random.choice(USER_AGENT_POOL),
        "Accept": "text/plain, application/json, */*",
        "Accept-Encoding": "gzip, deflate, br",
    }

    last_status_code = None

    logger.debug(
        f"Starting fetch for {sanitized_source} with effective timeout {effective_timeout}s "
        f"(Backoff: {backoff}s, Retries: {max_retries})"
    )

    for attempt in range(max_retries):
        loop = asyncio.get_running_loop()
        start_ts = loop.time()

        try:
            logger.debug(
                f"Fetch attempt {attempt + 1}/{max_retries} for {sanitized_source}"
            )
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
                    logger.info(f"High Jitter detected for {source}: {jitter:.2f}s")

            if result.success:
                # [FIX] Handle bytes vs str for content preview
                if isinstance(result.content, bytes):
                    preview_text = (
                        result.content[:50]
                        .decode("utf-8", errors="replace")
                        .replace("\n", "\\n")
                    )
                else:
                    preview_text = str(result.content)[:50].replace("\n", "\\n")

                content_type = result.headers.get("Content-Type", "unknown")
                content_len = result.headers.get("Content-Length", "unknown")

                logger.info(
                    f"Successfully fetched {len(result.content)} bytes from {sanitized_source} "
                    f"[Type: {content_type}, Len: {content_len}] "
                    f"(Time: {result.response_time:.2f}s, Timeout: {effective_timeout}s). "
                    f"Preview: {preview_text}..."
                )
                # Optional detailed headers at debug level only
                if logger.isEnabledFor(logging.DEBUG):
                    server_header = result.headers.get("Server", "unknown")
                    date_header = result.headers.get("Date", "unknown")
                    logger.debug(
                        f"Response headers (sanitized) for {sanitized_source}: "
                        f"Server={server_header}, Date={date_header}"
                    )
            else:
                logger.warning(
                    f"Fetch succeeded at network level but returned no valid content/success flag for {sanitized_source}. "
                    f"Status Code: {result.status_code if result.status_code else 'Unknown'}. "
                    f"Error: {result.error}"
                )

            if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
                breaker = await breaker_manager.get_breaker(host)
                await breaker.record_success()

            return result

        except RateLimitError as e:
            last_error = str(e)
            wait = e.retry_after if e.retry_after else backoff
            logger.warning(
                f"Rate limited by {host}. Waiting {wait:.2f}s before retry (Attempt {attempt+1}/{max_retries})."
            )
            await asyncio.sleep(wait + random.uniform(0, 0.5))
            backoff = min(backoff * 2, 60)

        except (httpx.HTTPError, asyncio.TimeoutError, ValueError) as e:
            # Capture status code if available in exception
            if isinstance(e, httpx.HTTPStatusError):
                last_status_code = e.response.status_code
                logger.warning(
                    f"HTTP Error {last_status_code} for {sanitized_source}: {e}"
                )
                if last_status_code == 404:
                    logger.info(
                        f"Source not found (404): {sanitized_source} - check URL validity"
                    )
                elif last_status_code == 403:
                    logger.warning(
                        f"Access forbidden (403): {sanitized_source} - check permissions/geo-block or user-agent"
                    )
                elif last_status_code >= 500:
                    logger.warning(
                        f"Server error ({last_status_code}) from {sanitized_source}"
                    )

            elif isinstance(e, asyncio.TimeoutError):
                logger.warning(
                    f"Timeout fetching {sanitized_source} after {per_attempt_timeout}s. "
                    f"Consider increasing timeout or checking network."
                )

            last_error = str(e)
            if controller:
                await controller.record(host, float(per_attempt_timeout), False)

            # Only record circuit breaker failure for actual server errors
            # 404/410 mean "resource not found" - the server is working fine
            # 403 means "forbidden" - could be geo-block, not server failure
            if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
                if last_status_code is None or last_status_code in SERVER_ERROR_CODES:
                    breaker = await breaker_manager.get_breaker(host)
                    await breaker.record_failure()
                    if await breaker.is_open():
                        logger.warning(
                            f"Circuit breaker TRIPPED for {host} due to server errors."
                        )
                else:
                    logger.debug(
                        f"Not counting {last_status_code} as circuit breaker failure for {host}"
                    )

            # If it's a 404 (Not Found) or 410 (Gone), retrying is futile.
            if last_status_code in (404, 410):
                # Record failure signals before aborting to keep controllers accurate
                try:
                    if controller:
                        await controller.record(host, float(per_attempt_timeout), False)
                    if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
                        breaker = await breaker_manager.get_breaker(host)
                        await breaker.record_failure()
                    # Inform adaptive timeout tracker of the failure for this attempt
                    if timeout_tracker is not None:
                        await timeout_tracker.record_attempt(
                            host, float(per_attempt_timeout), success=False
                        )
                except (asyncio.CancelledError, KeyboardInterrupt):
                    raise
                except Exception:
                    logger.debug(
                        "Failed to record controller/circuit-breaker/timeout state on permanent error",
                        exc_info=True,
                    )

                logger.info(
                    f"Aborting retries for {sanitized_source} due to permanent error status code: {last_status_code}"
                )
                return FetchResult(
                    False,
                    source,
                    error=f"Permanent Error: {last_status_code}",
                    status_code=last_status_code,
                )

            # Don't sleep on the last attempt
            if attempt < max_retries - 1:
                wait = min(backoff, 30)
                logger.info(
                    f"Retrying {sanitized_source} in {wait}s due to error: {last_error} "
                    f"(Attempt {attempt+1}/{max_retries}, Status: {last_status_code or 'N/A'})"
                )
                await asyncio.sleep(wait + random.uniform(0, 0.3))
                backoff = min(backoff * 2, 60)

        except Exception as e:
            logger.exception("Unexpected error fetching %s: %s", sanitized_source, e)
            last_error = f"Unexpected error: {str(e)}"
            if attempt < max_retries - 1:
                wait = min(backoff, 30)
                logger.info(
                    f"Retrying {sanitized_source} in {wait}s after unexpected error "
                    f"(Attempt {attempt+1}/{max_retries})"
                )
                await asyncio.sleep(min(backoff, 30))
                backoff = min(backoff * 2, 60)

    return FetchResult(
        False,
        source,
        error=f"Max retries exceeded: {last_error}",
        status_code=last_status_code,
    )
