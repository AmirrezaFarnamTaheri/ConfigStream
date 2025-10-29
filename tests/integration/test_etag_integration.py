import pytest
import httpx
import respx

from configstream.fetcher import fetch_from_source


@pytest.mark.asyncio
@respx.mock
async def test_etag_304_path():
    """Test the ETag 304 cache-hit path."""
    etag_value = '"test-etag"'
    url = "http://testserver/etag"

    def etag_side_effect(request):
        if request.headers.get("if-none-match") == etag_value:
            return httpx.Response(304)
        return httpx.Response(200, text="vmess://config", headers={"ETag": etag_value})

    route = respx.get(url).mock(side_effect=etag_side_effect)

    etag_cache = {}
    async with httpx.AsyncClient() as client:
        # First request should get a 200 and populate the cache
        result1 = await fetch_from_source(client, url, etag_cache=etag_cache)

    assert result1.status_code == 200
    assert len(result1.configs) == 1
    assert etag_cache.get(url, {}).get("etag") == etag_value

    async with httpx.AsyncClient() as client:
        # Second request should get a 304
        result2 = await fetch_from_source(client, url, etag_cache=etag_cache)

    assert result2.status_code == 304
    assert route.call_count == 2
