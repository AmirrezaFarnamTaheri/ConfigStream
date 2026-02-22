# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Fetcher worker components: Models, Utils, and Single Fetch Logic.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from configstream.config import AppSettings
# Import CircuitBreakerManager with TYPE_CHECKING guard if cyclic import issues arise,
# but here it is likely fine.
from configstream.circuit_breaker import CircuitBreakerManager

logger = logging.getLogger(__name__)


# --- Models ---

# Allow override via env for low-memory environments
# Default 0 means unlimited (managed via AppSettings in config.py)
MAX_RESPONSE_SIZE = 0


class FetchResult:
    """Container for fetch results with performance metadata."""

    __slots__ = (
        "success",
        "source",
        "content",
        "error",
        "response_time",
        "status_code",
        "headers",
    )

    def __init__(
        self,
        success: bool,
        source: str,
        content: str = "",
        error: str | None = None,
        response_time: float | None = None,
        status_code: int | None = None,
        headers: dict[str, Any] | None = None,
    ):
        self.success = success
        self.source = source
        self.content = content
        self.error = error
        self.response_time = response_time
        self.status_code = status_code
        self.headers = headers or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "success": self.success,
            "content_length": len(self.content),
            "error": self.error,
            "response_time": self.response_time,
            "status_code": self.status_code,
            "headers": self.headers,
        }


class FetcherError(Exception):
    """Base exception for fetcher-related errors."""


class RateLimitError(FetcherError):
    """Raised when an HTTP 429 Rate Limit is detected."""

    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after
        msg = (
            f"Rate limited. Retry after {retry_after:.1f}s"
            if retry_after
            else "Rate limited."
        )
        super().__init__(msg)


# --- Utils ---


def parse_retry_after(header: str | None) -> float | None:
    """Parse Retry-After header to seconds."""
    if not header:
        return None
    try:
        if header.isdigit():
            return float(header)
        parsed = parsedate_to_datetime(header)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0.0, (parsed - now).total_seconds())
    except Exception:
        return None


# --- Worker Logic ---


async def fetch_single_source(
    client: httpx.AsyncClient,
    source: str,
    headers: dict,
    max_response_size: int,
    app_settings: AppSettings,
    per_attempt_timeout: float,
    start_ts: float,
    loop: asyncio.AbstractEventLoop,
    circuit_breaker_manager: Optional[CircuitBreakerManager] = None,
) -> FetchResult:
    """
    Executes a single fetch attempt with strict size limits and error mapping.
    """
    domain: Optional[str] = None
    if circuit_breaker_manager:
        try:
            domain = urlparse(source).netloc
        except Exception:
            pass

    # Circuit Breaker Check
    if domain and circuit_breaker_manager:
        breaker = await circuit_breaker_manager.get_breaker(domain)
        if await breaker.is_open():
            if await breaker.should_log_open():
                logger.warning(f"Circuit open for domain {domain}, skipping {source}")
            return FetchResult(False, source, error="Circuit Open")

    try:
        enforce_limit = max_response_size > 0
        # Streaming Request to enforce size limit
        # We assume standard streaming as hedging is complex to stream
        async with client.stream(
            "GET",
            source,
            headers=headers,
            timeout=per_attempt_timeout,
            follow_redirects=True,
        ) as response:
            response_time = loop.time() - start_ts
            status = response.status_code

            # Rate Limit Handling
            if status == 429:
                retry_after = parse_retry_after(response.headers.get("Retry-After"))
                raise RateLimitError(retry_after)

            if status >= 400:
                response.raise_for_status()

            # Content Length Header Check
            content_len_header = response.headers.get("Content-Length")
            if enforce_limit and content_len_header:
                try:
                    cl_size = int(content_len_header)
                except (TypeError, ValueError):
                    cl_size = None  # Malformed header, rely on streamed size checks
                if cl_size is not None and cl_size > max_response_size:
                    raise ValueError(
                        f"Response too large (header): {content_len_header} bytes"
                    )

            # Stream Content (Binary)
            content_parts = []
            current_size = 0
            # Use aiter_bytes for binary safety
            async for chunk in response.aiter_bytes():
                chunk_len = len(chunk)
                current_size += chunk_len
                if enforce_limit and current_size > max_response_size:
                    raise ValueError(
                        f"Response too large (streamed): >{max_response_size} bytes"
                    )
                content_parts.append(chunk)

            # Join binary parts
            content_bytes = b"".join(content_parts)

            # Try to decode to string for compatibility, fallback to safe string if binary
            try:
                content_str = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    content_str = content_bytes.decode("latin-1")
                except Exception:
                    # Last resort fallback if it's purely binary garbage but we need a string
                    content_str = content_bytes.decode("utf-8", errors="replace")

            # Circuit Breaker Success
            if domain and circuit_breaker_manager:
                breaker = await circuit_breaker_manager.get_breaker(domain)
                await breaker.record_success()

            return FetchResult(
                True,
                source,
                content=content_str,
                response_time=response_time,
                status_code=status,
                headers=dict(response.headers),
            )

    except httpx.HTTPError as e:
        # Circuit Breaker Failure
        if domain and circuit_breaker_manager:
            breaker = await circuit_breaker_manager.get_breaker(domain)
            await breaker.record_failure()
        raise e
    except Exception as e:
         # Capture other errors too
        if domain and circuit_breaker_manager:
            breaker = await circuit_breaker_manager.get_breaker(domain)
            await breaker.record_failure()
        raise e
