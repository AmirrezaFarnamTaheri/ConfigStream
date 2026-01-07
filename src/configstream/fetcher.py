# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Production Fetcher Module.
Refactored into `src/configstream/fetcher_core/` for modularity.
This module now serves as a facade for backward compatibility.
"""

import httpx
from typing import Optional

from .fetcher_core.orchestrator import fetch_from_source
from .fetcher_core.batch import fetch_multiple_sources
from .fetcher_core.constants import MAX_RESPONSE_SIZE
from .fetcher_core.models import FetchResult, RateLimitError
from .config import AppSettings

__all__ = [
    "fetch_from_source",
    "fetch_multiple_sources",
    "MAX_RESPONSE_SIZE",
    "FetchResult",
    "RateLimitError",
    "Fetcher",
]


class Fetcher:
    """
    Facade class for backward compatibility.
    Wraps the functional fetcher API.
    """

    def __init__(self, settings: Optional[AppSettings] = None):
        self.settings = settings or AppSettings()

    async def fetch_text(self, url: str) -> Optional[str]:
        """
        Fetches text content from a URL using the orchestrator.
        """
        # Use configured timeout
        timeout = getattr(self.settings, "SOURCE_FETCH_TIMEOUT", 30.0)

        # [AUDIT FIX] Add explicit connection limits to prevent resource exhaustion
        limits = httpx.Limits(max_keepalive_connections=100, max_connections=500)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, limits=limits) as client:
            result = await fetch_from_source(
                client=client, source=url, app_settings=self.settings
            )

            if result.success and result.content:
                if isinstance(result.content, bytes):
                    return result.content.decode("utf-8", errors="replace")
                return str(result.content)

            return None
