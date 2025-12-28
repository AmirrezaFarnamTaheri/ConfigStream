"""
Production Fetcher Module.
Refactored into `src/configstream/fetcher_core/` for modularity.
This module now serves as a facade for backward compatibility.
"""

from typing import Optional

import httpx

from .config import AppSettings
from .fetcher_core.batch import fetch_multiple_sources
from .fetcher_core.constants import MAX_RESPONSE_SIZE
from .fetcher_core.models import FetchResult, RateLimitError
from .fetcher_core.orchestrator import fetch_from_source

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
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            result = await fetch_from_source(
                client=client, source=url, app_settings=self.settings
            )

            if result.success and result.content:
                if isinstance(result.content, bytes):
                    return result.content.decode("utf-8", errors="replace")
                return str(result.content)

            return None
