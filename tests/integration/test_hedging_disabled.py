import pytest
from aiohttp import web
from unittest.mock import patch

from configstream.fetcher import fetch_multiple_sources


@pytest.mark.asyncio
async def test_fetch_works_with_hedging_disabled(http_client_factory):
    """
    Verify that the fetcher works correctly when hedging is disabled.
    This test acts as a control to isolate the hedging logic as the source of failures.
    """
    app = web.Application()

    async def handler(request):
        return web.Response(text="vmess://config")

    app.router.add_get("/fast", handler)
    client = await http_client_factory(app)

    # Disable performance features to see if the base fetch logic works.
    with patch("configstream.fetcher.AppSettings") as mock_settings:
        settings = mock_settings.return_value
        settings.HEDGING_ENABLED = False
        settings.CIRCUIT_BREAKER_ENABLED = False  # Disable to prevent TypeError

        results = await fetch_multiple_sources([f"{client.base_url}/fast"], client=client)

    assert results[f"{client.base_url}/fast"].success is True
    assert results[f"{client.base_url}/fast"].error is None
