from __future__ import annotations

import asyncio
import logging
import httpx

from .models import FetchResult, RateLimitError
from .utils import parse_retry_after
from ..config import AppSettings

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

            # Stream Content
            content_parts = []
            current_size = 0
            async for chunk in response.aiter_text():
                chunk_len = len(chunk.encode("utf-8"))  # Approximation
                current_size += chunk_len
                if current_size > max_response_size:
                    raise ValueError(
                        f"Response too large (streamed): >{max_response_size} bytes"
                    )
                content_parts.append(chunk)

            content = "".join(content_parts)

            return FetchResult(
                True,
                source,
                content=content,
                response_time=response_time,
                status_code=status,
            )

    except httpx.HTTPError as e:
        raise e
