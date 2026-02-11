# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Fetcher core package.

Provides the multi-layer fetch stack:
- ``fetch_single_source`` – single-attempt streaming fetch with size limits.
- ``fetch_from_source``   – robust orchestrator with retries, circuit breaking,
                            adaptive timeouts, and rate limiting.
- ``fetch_multiple_sources`` – batch entry point with concurrency control.
"""

from .worker import fetch_single_source
from .orchestrator import fetch_from_source
from .batch import fetch_multiple_sources
from .models import FetchResult

__all__ = [
    "fetch_single_source",
    "fetch_from_source",
    "fetch_multiple_sources",
    "FetchResult",
]
