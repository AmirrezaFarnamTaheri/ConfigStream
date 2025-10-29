import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from configstream.dns_cache import DNSCache
from configstream.dns_prewarm import prewarm_dns_cache


@pytest.mark.asyncio
async def test_dns_cache_resolve_and_cache():
    cache = DNSCache(ttl=10)

    with patch('asyncio.get_running_loop') as mock_loop:
        mock_loop.return_value.getaddrinfo = AsyncMock(return_value=[(None, None, None, None, ('1.2.3.4', 0))])

        # First call should resolve and cache
        addr = await cache.resolve("example.com")
        assert addr == "1.2.3.4"
        mock_loop.return_value.getaddrinfo.assert_called_once_with(
            "example.com", None, family=0, type=1
        )

        # Second call should be a cache hit
        addr2 = await cache.resolve("example.com")
        assert addr2 == "1.2.3.4"
        mock_loop.return_value.getaddrinfo.assert_called_once()  # No new call


@pytest.mark.asyncio
async def test_prewarm_dns_cache():
    sources = [
        "http://example.com/1",
        "https://example.com/2",
        "http://google.com/3",
        "http://example.com/4",
    ]

    with patch('configstream.dns_prewarm.DEFAULT_CACHE.resolve') as mock_resolve:
        await prewarm_dns_cache(sources, top_n=1)

        # Should only resolve the most common host
        mock_resolve.assert_called_once_with("example.com")
