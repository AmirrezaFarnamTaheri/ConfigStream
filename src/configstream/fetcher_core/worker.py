from __future__ import annotations

import asyncio
import logging

import httpx

from ..config import AppSettings
from .models import FetchResult, RateLimitError
from .utils import parse_retry_after

logger = logging.getLogger(__name__)


async def fetch_single_source(
    client: httpx.AsyncClient,
    source: str,
    headers: dict,
    max_response_size: int,
    app_settings: AppSettings,
    per_attempt_timeout: float,
    start_ts: float,
    loop: asyncio.AbstractEventLoop,
) -> FetchResult:
    """
    Executes a single fetch attempt with strict size limits and error mapping.
    """
    try:
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
            if content_len_header and int(content_len_header) > max_response_size:
                raise ValueError(
                    f"Response too large (header): {content_len_header} bytes"
                )

            # Stream Content (Binary)
            content_parts = []
            current_size = 0
            # [FIX] Use aiter_bytes for binary safety
            async for chunk in response.aiter_bytes():
                chunk_len = len(chunk)
                current_size += chunk_len
                if current_size > max_response_size:
                    raise ValueError(
                        f"Response too large (streamed): >{max_response_size} bytes"
                    )
                content_parts.append(chunk)

            # Join binary parts
            content_bytes = b"".join(content_parts)

            # [FIX] Try to decode to string for compatibility, fallback to safe string if binary
            try:
                content_str = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    content_str = content_bytes.decode("latin-1")
                except Exception:
                    # Last resort fallback if it's purely binary garbage but we need a string
                    content_str = content_bytes.decode("utf-8", errors="replace")

            return FetchResult(
                True,
                source,
                content=content_str,
                response_time=response_time,
                status_code=status,
                headers=dict(response.headers),
            )

    except httpx.HTTPError as e:
        raise e
