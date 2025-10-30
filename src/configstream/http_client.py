"""Shared HTTP client utilities for ConfigStream."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx

from .dns_cache import DEFAULT_CACHE
from .config import AppSettings

try:  # pragma: no cover - optional dependency used only when available
    import h2  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    HTTP2_AVAILABLE = False
else:  # pragma: no cover
    HTTP2_AVAILABLE = True

DEFAULT_TIMEOUT = httpx.Timeout(20.0, connect=10.0, read=15.0)
POOL_LIMITS = httpx.Limits(max_keepalive_connections=100, max_connections=200)


class CachedDNS_AsyncHTTPTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        app_settings = AppSettings()
        if app_settings.DNS_CACHE_ENABLED:
            host = request.url.host
            cached_ip = await DEFAULT_CACHE.resolve(host)
            if cached_ip:
                # Rebuild the URL with the cached IP, preserving other components
                url = request.url
                request.url = url.copy_with(host=cached_ip)
                request.headers["Host"] = host

        return await super().handle_async_request(request)


@asynccontextmanager
async def get_client(retries: int = 0) -> AsyncIterator[httpx.AsyncClient]:
    """Yield a configured AsyncClient with sane defaults.

    The client enables HTTP/2, follows redirects, and sets a deterministic
    user agent so providers can more easily identify ConfigStream traffic.
    """
    app_settings = AppSettings()
    transport: httpx.AsyncHTTPTransport
    if app_settings.DNS_CACHE_ENABLED:
        transport = CachedDNS_AsyncHTTPTransport(retries=retries)
    else:
        transport = httpx.AsyncHTTPTransport(retries=retries)

    async with httpx.AsyncClient(
        http2=HTTP2_AVAILABLE,
        timeout=DEFAULT_TIMEOUT,
        limits=POOL_LIMITS,
        headers={
            "accept": "*/*",
            "user-agent": "ConfigStream/1 (+https://github.com/AmirrezaFarnamTaheri/ConfigStream)",
        },
        follow_redirects=True,
        transport=transport,
    ) as client:
        yield client
