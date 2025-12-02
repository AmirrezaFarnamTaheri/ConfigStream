"""
Production Fetcher Module.
Refactored into `src/configstream/fetcher_core/` for modularity.
This module now serves as a facade for backward compatibility.
"""

from .fetcher_core.orchestrator import fetch_from_source
from .fetcher_core.batch import fetch_multiple_sources
from .fetcher_core.constants import MAX_RESPONSE_SIZE
from .fetcher_core.models import FetchResult, RateLimitError

__all__ = [
    "fetch_from_source",
    "fetch_multiple_sources",
    "MAX_RESPONSE_SIZE",
    "FetchResult",
    "RateLimitError",
]
