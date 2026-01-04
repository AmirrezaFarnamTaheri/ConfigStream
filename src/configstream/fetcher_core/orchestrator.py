# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import random
from urllib.parse import urlparse
from typing import Optional, Any, TYPE_CHECKING
import httpx
from types import SimpleNamespace

if TYPE_CHECKING:
    from configstream.config import AppSettings
    from configstream.fetcher_core.models import FetchResult

logger = logging.getLogger(__name__)

# Constants inferred from tests
MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB default?
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
    retry_delay: float = 1.0
) -> Any:
    """
    Robust fetcher implementation handling retries, circuit breaking, rate limiting,
    and response size limits.
    """

    # [FIX] Validate URL
    if not source or not source.startswith(("http://", "https://")):
        return SimpleNamespace(success=False, content=None, error="Invalid URL", status_code=0)

    # Circuit Breaker Check
    if breaker_manager:
        # [FIX] Extract host from URL to use as breaker key (matching test expectation)
        try:
            parsed = urlparse(source)
            host = parsed.netloc
            # Remove port if present? Tests use "broken.com". If URL is http://broken.com, netloc is broken.com.
            # If URL is http://broken.com:80, netloc is broken.com:80.
            # Assuming test uses standard logic. If test used `f"http://{host}"`, host="broken.com".
            # netloc will be "broken.com".
            # If host was "broken.com:8080", netloc is "broken.com:8080".
            # This seems correct for keying.
            key = host
        except Exception:
            key = source

        breaker = await breaker_manager.get_breaker(key)

        is_open = breaker.is_open()
        if asyncio.iscoroutine(is_open):
            is_open = await is_open

        if is_open:
            return SimpleNamespace(success=False, content=None, error="Circuit Breaker Open", status_code=0)

    # Rate Limiter Pre-check
    if rate_limiter:
        if not await rate_limiter.is_allowed(source):
            wait_time = await rate_limiter.get_wait_time(source)
            if wait_time > 0:
                await asyncio.sleep(wait_time)

    headers = {"User-Agent": random.choice(USER_AGENTS)}
    attempt = 0
    last_error = None

    while attempt < max_retries:
        try:
            # Jitter / Timeout Tracking
            timeout = 30.0
            if timeout_tracker:
                timeout = timeout_tracker.get_timeout(source)
                jitter = await timeout_tracker.get_jitter(source)
                if jitter > 2.0:
                    logger.info(f"High Jitter detected for {source}: {jitter}s")

            async with client.stream("GET", source, headers=headers, timeout=timeout, follow_redirects=True) as response:

                # Check Status
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else 2.0
                    await asyncio.sleep(wait)
                    attempt += 1
                    last_error = "Rate limited"
                    continue

                if response.status_code in [404, 410]:
                    return SimpleNamespace(success=False, content=None, error=f"Permanent Error: {response.status_code}", status_code=response.status_code)

                if response.status_code >= 500:
                    attempt += 1
                    last_error = f"HTTP {response.status_code}"
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue

                # Content Length Check
                content_len = response.headers.get("Content-Length")
                if content_len and int(content_len) > MAX_RESPONSE_SIZE:
                    return SimpleNamespace(success=False, content=None, error="Response too large", status_code=response.status_code)

                # Stream Content
                content = b""
                async for chunk in response.aiter_bytes():
                    content += chunk
                    if len(content) > MAX_RESPONSE_SIZE:
                        return SimpleNamespace(success=False, content=None, error="Response too large", status_code=response.status_code)

                # Decode
                text_content = content.decode("utf-8", errors="ignore")

                if response.status_code == 200 and (not text_content or not text_content.strip()):
                    attempt += 1
                    last_error = "Empty content with 200 OK"
                    continue

                return SimpleNamespace(success=True, content=text_content, status_code=response.status_code, error=None)

        except Exception as e:
            last_error = str(e)
            attempt += 1
            await asyncio.sleep(retry_delay)

    return SimpleNamespace(success=False, content=None, error=f"Max retries exceeded: {last_error}", status_code=0)

class FetchOrchestrator:
    pass
