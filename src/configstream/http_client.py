"""
Shared HTTP client utilities for ConfigStream.
Provides a centralized, optimized AsyncClient with connection pooling and HTTP/2 support.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx

from .dns_cache import DEFAULT_CACHE
from .config import AppSettings

# Check for HTTP/2 support
try:
    import h2  # noqa: F401
    HTTP2_AVAILABLE = True
except ModuleNotFoundError:
    HTTP2_AVAILABLE = False


class CachedDNS_AsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """
    Custom Transport that utilizes a centralized DNS cache.

    NOTE: DNS caching is currently only applied to HTTP requests.
    For HTTPS, we rely on the standard resolver to avoid SSL Hostname Mismatch errors.
    Forcing an IP connection with HTTPS requires manual Host header manipulation
    and a custom SSLContext that trusts the injected Host header, which adds
    significant complexity and security risk (MITM).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._settings = AppSettings()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if self._settings.DNS_CACHE_ENABLED and request.url.scheme == "http":
            host = request.url.host
            cached_ip = await DEFAULT_CACHE.resolve(host)

            if cached_ip:
                # Rewrite the URL to use the IP address
                # This works for HTTP because the Host header is preserved/set separately
                request.url = request.url.copy_with(host=cached_ip)
                if "Host" not in request.headers:
                    request.headers["Host"] = host

        return await super().handle_async_request(request)


@asynccontextmanager
async def get_client(retries: int = 0) -> AsyncIterator[httpx.AsyncClient]:
    """
    Yield a configured AsyncClient with production-grade defaults.

    Features:
    - HTTP/2 Support (if available)
    - Connection Pooling (configurable limits)
    - Automatic Redirect Following
    - Custom Transport (DNS Caching)
    """
    app_settings = AppSettings()

    # Configure Connection Pool Limits
    limits = httpx.Limits(
        max_keepalive_connections=100,
        max_connections=app_settings.PER_HOST_MAX_CONCURRENCY * 10,  # Allow broad concurrency
        keepalive_expiry=30.0
    )

    # Configure Transport
    transport_cls = CachedDNS_AsyncHTTPTransport if app_settings.DNS_CACHE_ENABLED else httpx.AsyncHTTPTransport
    transport = transport_cls(
        retries=retries,
        limits=limits,
        http2=HTTP2_AVAILABLE
    )

    # Configure Client
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
