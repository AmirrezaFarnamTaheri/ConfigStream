import httpx
import pytest
import respx

from configstream.fetcher import fetch_from_source


@pytest.mark.asyncio
async def test_fetch_404_abort():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as respx_mock:
            # Mock 404 response
            respx_mock.get("/missing").mock(return_value=httpx.Response(404))

            # This should return immediately after first 404, not retry
            result = await fetch_from_source(
                client, "https://example.com/missing", max_retries=3
            )

            assert not result.success
            assert result.status_code == 404
            assert "Permanent Error: 404" in result.error
            assert respx_mock.calls.call_count == 1  # Should only call once


@pytest.mark.asyncio
async def test_fetch_410_abort():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as respx_mock:
            # Mock 410 response
            respx_mock.get("/gone").mock(return_value=httpx.Response(410))

            result = await fetch_from_source(
                client, "https://example.com/gone", max_retries=3
            )

            assert not result.success
            assert result.status_code == 410
            assert "Permanent Error: 410" in result.error
            assert respx_mock.calls.call_count == 1


@pytest.mark.asyncio
async def test_fetch_500_retry():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as respx_mock:
            # Mock 500 response
            respx_mock.get("/error").mock(return_value=httpx.Response(500))

            # This should retry
            result = await fetch_from_source(
                client, "https://example.com/error", max_retries=2, retry_delay=0.01
            )

            assert not result.success
            # Should fail after max_retries
            # Since retries happen in loop 0..max_retries-1, actually 2 retries = 2 calls total?
            # Logic: range(max_retries) -> 0, 1. So 2 attempts.
            assert respx_mock.calls.call_count == 2
