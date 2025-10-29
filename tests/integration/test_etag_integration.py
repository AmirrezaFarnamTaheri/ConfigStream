import pytest
from aiohttp import web
import httpx

from configstream.fetcher import fetch_from_source


@pytest.mark.asyncio
async def test_etag_304_path(http_client_factory):
    """Test the ETag 304 cache-hit path."""
    app = web.Application()
    etag_value = '"test-etag"'

    async def handler(request):
        if request.headers.get("If-None-Match") == etag_value:
            return web.Response(status=304)
        return web.Response(text="vmess://config", headers={"ETag": etag_value})

    app.router.add_get("/etag", handler)
    client = await http_client_factory(app)

    etag_cache = {}

    # First request should get a 200 and populate the cache
    result1 = await fetch_from_source(client, f"{client.base_url}/etag", etag_cache=etag_cache)

    assert result1.status_code == 200
    assert len(result1.configs) == 1
    assert etag_cache[f"{client.base_url}/etag"]["etag"] == etag_value

    # Second request should get a 304
    result2 = await fetch_from_source(client, f"{client.base_url}/etag", etag_cache=etag_cache)

    assert result2.status_code == 304
