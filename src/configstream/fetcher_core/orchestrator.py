import asyncio
import logging
import random
from typing import Optional
from urllib.parse import urlparse
import httpx

from configstream.security.rate_limiter import RateLimiter
from configstream.concurrency_manager import ConcurrencyManager
from configstream.config import AppSettings
from configstream.circuit_breaker import CircuitBreakerManager
from configstream.adaptive_timeout import AdaptiveTimeout
from configstream.fetcher_core.models import FetchResult, RateLimitError
from configstream.fetcher_core.worker import fetch_single_source
from configstream.security_validator import SecurityValidator
from configstream.fetcher_core.constants import MAX_RESPONSE_SIZE

# Integrate Source Manager
from configstream.source_quality import SourceQualityTracker

logger = logging.getLogger(__name__)


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
    quality_tracker: Optional[SourceQualityTracker] = None,
) -> FetchResult:
    """
    Fetch configurations from a source with full resilience logic.
    """
    if app_settings is None:
        app_settings = AppSettings()

    # --- Source Health Check ---
    source_manager = quality_tracker or SourceQualityTracker()

    # 1. URL Validation
    sanitized_source = SecurityValidator.sanitize_log_message(source)
    host: str = ""
    try:
        parsed = urlparse(source)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {sanitized_source}")
        host = parsed.netloc
    except Exception as e:
        logger.debug(f"URL validation failed for {sanitized_source}: {e}")
        source_manager.report_failure(source)
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
    last_error: Optional[str] = None

    # Standard headers (No ETag to force fresh content)
    headers = {
        "User-Agent": "ConfigStream/1.1",
        "Accept": "text/plain, application/json, */*",
        "Accept-Encoding": "gzip, deflate, br",
    }

    last_status_code: Optional[int] = None

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

            # Success (at least partial)
            if result.success and result.content:
                source_manager.report_success(source)  # <--- Track Success

                # [FIX] Handle bytes vs str for content preview
                preview_text = ""
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

                # Ensure result.response_time is treated as float for logging
                resp_time = float(result.response_time) if result.response_time else 0.0

                logger.debug(
                    f"Successfully fetched {len(result.content or '')} bytes from {sanitized_source} "
                    f"[Type: {content_type}, Len: {content_len}] "
                    f"(Time: {resp_time:.2f}s, Timeout: {effective_timeout}s). "
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

                # [FIX] Only record success if we actually succeeded
                if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
                    breaker = await breaker_manager.get_breaker(host)
                    await breaker.record_success()

                return result

            else:
                # [FIX] "Optimistic Failure" Bug:
                # Previously, we returned the failed result immediately.
                # Now, we force a retry by treating this as a non-exception failure
                # unless it's the last attempt.
                logger.warning(
                    f"Fetch succeeded at network level but returned no valid content/success flag for {sanitized_source}. "
                    f"Status Code: {result.status_code if result.status_code else 'Unknown'}. "
                    f"Error: {result.error}"
                )
                last_error = f"Invalid Content: {result.error}"
                # Fall through to retry logic
                if attempt < max_retries - 1:
                    wait = min(backoff, 30)
                    logger.info(
                        f"Retrying {sanitized_source} in {wait}s due to invalid content "
                        f"(Attempt {attempt+1}/{max_retries})"
                    )
                    await asyncio.sleep(wait + random.uniform(0, 0.3))
                    backoff = min(backoff * 2, 60)
                    continue
                else:
                    # Last attempt failed
                    break

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
                # pylint: disable=no-member
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
            if app_settings.CIRCUIT_BREAKER_ENABLED and breaker_manager:
                breaker = await breaker_manager.get_breaker(host)
                await breaker.record_failure()
                if await breaker.is_open():
                    logger.warning(
                        f"Circuit breaker TRIPPED for {host} due to failures."
                    )

            # If it's a 404 (Not Found) or 410 (Gone), retrying is futile.
            if last_status_code in (404, 410):
                # FIX: Removed duplicate controller.record() and breaker.record_failure() calls
                # These are already recorded above in lines 226-234 for the general error case.
                # Only record source failure and timeout tracker here (not duplicated above).
                try:
                    # Inform adaptive timeout tracker of the failure for this attempt
                    if timeout_tracker is not None:
                        await timeout_tracker.record_attempt(
                            host, float(per_attempt_timeout), success=False
                        )

                    source_manager.report_failure(source)  # <--- Track Failure
                except (
                    asyncio.CancelledError,
                    KeyboardInterrupt,
                ):  # pylint: disable=try-except-raise
                    raise
                except Exception:
                    logger.debug(
                        "Failed to record timeout/source state on permanent error",
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
                # [FIX] Downgrade retry logs to DEBUG to reduce spam, unless it's a 4xx/5xx error worth noting
                log_level = logging.INFO
                if last_status_code and 400 <= last_status_code < 500:
                    log_level = logging.DEBUG  # Client errors on source side are common

                logger.log(
                    log_level,
                    f"Retrying {sanitized_source} in {wait}s due to error: {last_error} "
                    f"(Attempt {attempt+1}/{max_retries}, Status: {last_status_code or 'N/A'})",
                )
                await asyncio.sleep(wait + random.uniform(0, 0.3))
                backoff = min(backoff * 2, 60)

        except Exception as e:
            # Log exception but handle retry logic gracefully
            logger.error(
                "Unexpected error fetching %s: %s", sanitized_source, e, exc_info=True
            )
            last_error = f"Unexpected error: {str(e)}"
            if attempt < max_retries - 1:
                wait = min(backoff, 30)
                logger.info(
                    f"Retrying {sanitized_source} in {wait}s after unexpected error "
                    f"(Attempt {attempt+1}/{max_retries})"
                )
                await asyncio.sleep(min(backoff, 30))
                backoff = min(backoff * 2, 60)

    # If we get here, all retries failed
    source_manager.report_failure(source)  # <--- Track Failure

    return FetchResult(
        False,
        source,
        error=f"Max retries exceeded: {last_error}",
        status_code=last_status_code,
    )
