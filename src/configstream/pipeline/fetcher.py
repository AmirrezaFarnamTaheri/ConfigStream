# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import time
from typing import Optional, Any, Dict
import httpx

from .interfaces import IFetcher, FetchResult
from configstream.security_validator import SecurityValidator
from configstream.fetcher import _reject_source_url, _resolve_redirect_url

logger = logging.getLogger(__name__)

class HttpFetcher(IFetcher):
    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: Any,
        breaker_manager: Optional[Any] = None,
        timeout_tracker: Optional[Any] = None,
    ):
        self.client = client
        self.settings = settings
        self.breaker_manager = breaker_manager
        self.timeout_tracker = timeout_tracker

    async def fetch(self, source: str) -> FetchResult:
        start_time = time.perf_counter()
        safe_source = SecurityValidator.sanitize_log_message(source)

        # 1. URL Validation
        url_error = _reject_source_url(
            source,
            block_private_networks=bool(self.settings.FETCH_BLOCK_PRIVATE_NETWORKS)
        )
        if url_error:
            return FetchResult(success=False, source=source, error=url_error)

        # 2. Fetch Logic (simplified version of the one in configstream.fetcher)
        # In a real scenario, we'd port more of the robust logic here.
        # For now, let's wrap a basic request to establish the contract.
        try:
            response = await self.client.get(
                source,
                timeout=getattr(self.settings, "FETCH_TIMEOUT", 10.0),
                follow_redirects=True
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            if response.status_code == 200:
                return FetchResult(
                    success=True,
                    source=source,
                    content=response.text,
                    status_code=response.status_code,
                    duration_ms=duration_ms
                )
            else:
                return FetchResult(
                    success=False,
                    source=source,
                    error=f"HTTP {response.status_code}",
                    status_code=response.status_code,
                    duration_ms=duration_ms
                )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return FetchResult(
                success=False,
                source=source,
                error=str(e),
                duration_ms=duration_ms
            )
