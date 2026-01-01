# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import httpx
from configstream.fetcher import fetch_from_source


@pytest.mark.asyncio
async def test_fetch_success(respx_mock):
    url = "https://example.com/sub"
    respx_mock.get(url).mock(return_value=httpx.Response(200, text="content"))

    async with httpx.AsyncClient() as client:
        result = await fetch_from_source(client, url)

    assert result.success is True
    assert result.content == "content"


@pytest.mark.asyncio
async def test_fetch_404(respx_mock):
    url = "https://example.com/404"
    respx_mock.get(url).mock(return_value=httpx.Response(404))

    async with httpx.AsyncClient() as client:
        result = await fetch_from_source(client, url)

    assert result.success is False
    # If 404, the fetcher returns success=False and status_code=404
    assert result.status_code == 404


@pytest.mark.asyncio
async def test_fetch_retry_on_error(respx_mock):
    url = "https://example.com/flaky"
    # First 2 fail, 3rd succeeds
    route = respx_mock.get(url)
    route.side_effect = [
        httpx.ConnectError("Fail 1"),
        httpx.ConnectError("Fail 2"),
        httpx.Response(200, text="Success"),
    ]

    async with httpx.AsyncClient() as client:
        result = await fetch_from_source(client, url, max_retries=3, retry_delay=0.01)

    assert result.success is True
    assert result.content == "Success"
    assert route.call_count == 3


@pytest.mark.asyncio
async def test_fetch_rate_limit(respx_mock):
    url = "https://example.com/ratelimit"
    # 429 then 200
    route = respx_mock.get(url)
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "0.1"}),
        httpx.Response(200, text="Done"),
    ]

    async with httpx.AsyncClient() as client:
        result = await fetch_from_source(client, url, max_retries=3)

    assert result.success is True
    assert route.call_count == 2
