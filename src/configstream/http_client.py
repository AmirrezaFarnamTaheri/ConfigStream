# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Shared HTTP client utilities for ConfigStream.
Provides a centralized, optimized AsyncClient with connection pooling and HTTP/2 support.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
import sniffio

from .config import AppSettings
from .security.transport import SecurityTransport

# Check for HTTP/2 support
try:
    import h2  # pylint: disable=unused-import # noqa: F401

    HTTP2_AVAILABLE = True
except ModuleNotFoundError:
    HTTP2_AVAILABLE = False


@asynccontextmanager
async def get_client(retries: int = 0) -> AsyncIterator[httpx.AsyncClient]:
    """
    Yield a configured AsyncClient with production-grade defaults.

    Features:
    - HTTP/2 Support (if available)
    - Connection Pooling (configurable limits)
    - Automatic Redirect Following
    - SecurityTransport (DNS Caching + Rebinding Protection)
    """
    app_settings = AppSettings()

    # Configure Connection Pool Limits
    # Add explicit bounds to prevent resource exhaustion
    max_conns = min(
        app_settings.PER_HOST_MAX_CONCURRENCY * 10,
        500,  # Hard cap at 500 connections
    )
    limits = httpx.Limits(
        max_keepalive_connections=100,
        max_connections=max_conns,  # Bounded concurrency
        keepalive_expiry=30.0,
    )

    # Configure Security Transport
    # This replaces the old CachedDNS_AsyncHTTPTransport by consolidating
    # DNS caching and DNS rebinding protection (IP pinning).
    transport = SecurityTransport(
        retries=retries,
        limits=limits,
        http2=HTTP2_AVAILABLE,
        block_private_networks=bool(app_settings.FETCH_BLOCK_PRIVATE_NETWORKS),
        dns_cache_enabled=bool(app_settings.DNS_CACHE_ENABLED),
    )

    # Configure Client
    token = sniffio.current_async_library_cvar.set("asyncio")
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=10.0, read=15.0),
            headers={
                "User-Agent": "ConfigStream/1.1 (+https://github.com/AmirrezaFarnamTaheri/ConfigStream)",
                "Accept": "text/plain, application/json, */*",
            },
            follow_redirects=True,
            transport=transport,
        ) as client:
            yield client
    finally:
        sniffio.current_async_library_cvar.reset(token)
