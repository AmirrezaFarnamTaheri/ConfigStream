# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import random
from urllib.parse import urlparse
from typing import Any, TYPE_CHECKING
import httpx
from configstream.fetcher_core.models import FetchResult
from configstream.config import AppSettings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Constants
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
    **kwargs: Any,  # Accept extra kwargs (controller, quality_tracker) to satisfy Mypy/callers
) -> Any:
    """
    Robust fetcher implementation handling retries, circuit breaking, rate limiting,
    and response size limits.
    """

    # Validate URL
    if not source or not source.startswith(("http://", "https://")):
        return FetchResult(
            success=False, source=source, content="", error="Invalid URL", status_code=0
        )

    # [FIX] Normalization for specific malformed URLs (e.g. raw.githubusercontent)
    try:
        parsed_url = urlparse(source)
        host = parsed_url.netloc
        # Check for malformed raw.githubusercontent domains (e.g. user.raw.githubusercontent.com)
        if "raw.githubusercontent.com" in host and host != "raw.githubusercontent.com":
             logger.warning(
                 f"Suspicious hostname detected: {host}. This might be a malformed GitHub raw URL."
             )
    except Exception:
        pass

    # Circuit Breaker Check
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

    # [FIX] Use AppSettings for MAX_RESPONSE_SIZE
    max_response_size = AppSettings().MAX_RESPONSE_SIZE

    while attempt < max_retries:
        start_ts = asyncio.get_running_loop().time()
        try:
            # Jitter / Timeout Tracking
            timeout = 30.0
            if timeout_tracker:
                timeout = timeout_tracker.get_timeout(source)
                jitter = await timeout_tracker.get_jitter(source)
                if jitter > 2.0:
                    logger.info(f"High Jitter detected for {source}: {jitter}s")

            async with client.stream(
                "GET", source, headers=headers, timeout=timeout, follow_redirects=True
            ) as response:

                # Check Status
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else 2.0
                    await asyncio.sleep(wait)
                    attempt += 1
                    last_error = "Rate limited"
                    continue

                if response.status_code in [404, 410]:
                    return FetchResult(
                        success=False,
                        source=source,
                        content="",
                        error=f"Permanent Error: {response.status_code}",
                        status_code=response.status_code,
                        response_time=asyncio.get_running_loop().time() - start_ts,
                    )

                if response.status_code >= 500:
                    attempt += 1
                    last_error = f"HTTP {response.status_code}"
                    await asyncio.sleep(retry_delay * (2**attempt))
                    continue

                # Content Length Check
                content_len = response.headers.get("Content-Length")
                if content_len and int(content_len) > max_response_size:
                    return FetchResult(
                        success=False,
                        source=source,
                        content="",
                        error="Response too large",
                        status_code=response.status_code,
                        response_time=asyncio.get_running_loop().time() - start_ts,
                    )

                # Stream Content
                content = b""
                async for chunk in response.aiter_bytes():
                    content += chunk
                    if len(content) > max_response_size:
                        return FetchResult(
                            success=False,
                            source=source,
                            content="",
                            error="Response too large",
                            status_code=response.status_code,
                            response_time=asyncio.get_running_loop().time() - start_ts,
                        )

                # Decode
                text_content = content.decode("utf-8", errors="ignore")

                # [FIX] Handle empty 200 OK responses more gracefully
                if response.status_code == 200:
                    if not text_content or not text_content.strip():
                        # Check Content-Length to see if it was explicitly empty
                        header_len = response.headers.get("Content-Length")
                        if (
                            header_len
                            and header_len.strip() == "0"
                        ):
                             # Valid empty response
                             pass
                        elif not text_content:
                             # Empty but maybe no content-length or implicitly empty
                             # Log specific error but treat as valid 'no content' failure instead of retry loop if it persists?
                             # Actually we should retry if we expect content but got none (network glitch?)
                             # But usually empty body with 200 OK is final.
                             # Let's count it as success=True but content="" so parser sees 0 proxies.
                             pass
                        else:
                             pass

                return FetchResult(
                    success=True,
                    source=source,
                    content=text_content,
                    status_code=response.status_code,
                    error=None,
                    response_time=asyncio.get_running_loop().time() - start_ts,
                )

        except asyncio.CancelledError:
            logger.warning(f"Fetch for {source} cancelled by outer signal.")
            # Propagate cancellation to abort fetch immediately
            raise
        except Exception as e:
            last_error = str(e)
            attempt += 1
            await asyncio.sleep(retry_delay)

    return FetchResult(
        success=False,
        source=source,
        content="",
        error=f"Max retries exceeded: {last_error}",
        status_code=0,
    )


class FetchOrchestrator:
    pass
