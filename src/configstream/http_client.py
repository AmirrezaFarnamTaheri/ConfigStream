"""Shared HTTP client utilities for ConfigStream."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx  # type: ignore[import-not-found]

try:  # pragma: no cover - optional dependency used only when available
    import h2  # type: ignore[import-not-found]  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    HTTP2_AVAILABLE = False
else:  # pragma: no cover
    HTTP2_AVAILABLE = True

DEFAULT_TIMEOUT = httpx.Timeout(20.0, connect=10.0, read=15.0)
POOL_LIMITS = httpx.Limits(max_keepalive_connections=100, max_connections=200)


@asynccontextmanager
async def get_client(retries: int = 0) -> AsyncIterator[httpx.AsyncClient]:
    """Yield a configured AsyncClient with sane defaults.

    The client enables HTTP/2, follows redirects, and sets a deterministic
    user agent so providers can more easily identify ConfigStream traffic.
    """
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
