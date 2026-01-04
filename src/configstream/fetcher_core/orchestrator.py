# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import random
from typing import Optional, Tuple, TYPE_CHECKING, Any
import aiohttp
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

if TYPE_CHECKING:
    from configstream.pipeline_core.models import PipelineStats
    from configstream.config import AppSettings
    from configstream.fetcher_core.models import FetchResult

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
]


class FetchOrchestrator:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError)
        ),
    )
    async def fetch_source(
        self, url: str, session: aiohttp.ClientSession
    ) -> Tuple[Optional[str], dict]:
        """
        Fetches content from a URL with retries and rotation.
        Returns (content, metadata).
        """
        metadata = {}
        try:
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            start_time = asyncio.get_running_loop().time()

            async with session.get(
                url, headers=headers, timeout=self.timeout, allow_redirects=True
            ) as response:
                metadata["status_code"] = response.status
                metadata["content_type"] = response.headers.get("Content-Type", "")

                if response.status == 200:
                    try:
                        # Try decoding as text
                        text = await response.text(encoding="utf-8", errors="ignore")

                        # [FIX] Optimistic Failure: Check if 200 OK but empty body
                        if not text or not text.strip():
                            logger.warning(f"Source {url} returned 200 OK but empty content. Retrying...")
                            raise ConnectionError("Empty content with 200 OK") # Trigger retry

                        metadata["fetch_duration"] = (
                            asyncio.get_running_loop().time() - start_time
                        )
                        return text, metadata
                    except Exception as e:
                        # If text decoding fails heavily (binary?), returns None
                        logger.debug(f"Failed to decode text from {url}: {e}")
                        return None, metadata
                else:
                    logger.debug(f"Source {url} returned status {response.status}")
                    return None, metadata

        except Exception as e:
            logger.debug(f"Error fetching {url}: {e}")
            raise e  # Allow tenacity to retry

    async def fetch_all(
        self, sources: list[str], max_concurrency: int = 10
    ) -> list[Tuple[str, str, dict]]:
        """
        Parallel fetch of multiple sources.
        Returns list of (url, content, metadata).
        """
        connector = aiohttp.TCPConnector(limit=max_concurrency, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for url in sources:
                if not url.strip() or url.startswith("#"):
                    continue
                tasks.append(self._safe_fetch(url, session))

            results = await asyncio.gather(*tasks)
            # Filter out failures (None content)
            return [r for r in results if r[1] is not None]

    async def _safe_fetch(
        self, url: str, session: aiohttp.ClientSession
    ) -> Tuple[str, Optional[str], dict]:
        try:
            content, meta = await self.fetch_source(url, session)
            return url, content, meta
        except Exception:
            return url, None, {}

# [BACKWARD COMPATIBILITY]
# The legacy Fetcher class in src/configstream/fetcher.py calls this function.
# We must implement it to match the signature expected by Fetcher.fetch_text
# which passes: client=httpx.AsyncClient, source=str, app_settings=AppSettings

async def fetch_from_source(
    client: httpx.AsyncClient,
    source: str,
    app_settings: "AppSettings" = None
) -> Any:
    """
    Standalone function used by legacy Fetcher facade.
    Returns a FetchResult-like object (or a SimpleNamespace for duck typing).
    """
    from types import SimpleNamespace

    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        response = await client.get(source, headers=headers)

        # Check for empty content (Optimistic Failure Fix)
        if response.status_code == 200:
             content = response.text
             if not content or not content.strip():
                  return SimpleNamespace(success=False, content=None, error="Empty content")
             return SimpleNamespace(success=True, content=content, status_code=200)
        else:
             return SimpleNamespace(success=False, content=None, status_code=response.status_code)

    except Exception as e:
        return SimpleNamespace(success=False, content=None, error=str(e))
