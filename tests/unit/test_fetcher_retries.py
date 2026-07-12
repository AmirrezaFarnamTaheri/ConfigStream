# SPDX-License-Identifier: AGPL-3.0-or-later
import httpx
import pytest
import respx

from configstream.config import AppSettings
from configstream.pipeline.fetcher import fetch_from_source


def _mocked_settings() -> AppSettings:
    settings = AppSettings()
    settings.FETCH_VALIDATE_DNS = False
    return settings


@pytest.mark.asyncio
async def test_fetch_404_abort():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as respx_mock:
            respx_mock.get("/missing").mock(return_value=httpx.Response(404))
            result = await fetch_from_source(
                client,
                "https://example.com/missing",
                max_retries=3,
                app_settings=_mocked_settings(),
            )

            assert not result.success
            assert result.status_code == 404
            assert "Permanent Error: 404" in result.error
            assert respx_mock.calls.call_count == 1


@pytest.mark.asyncio
async def test_fetch_410_abort():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as respx_mock:
            respx_mock.get("/gone").mock(return_value=httpx.Response(410))
            result = await fetch_from_source(
                client,
                "https://example.com/gone",
                max_retries=3,
                app_settings=_mocked_settings(),
            )

            assert not result.success
            assert result.status_code == 410
            assert "Permanent Error: 410" in result.error
            assert respx_mock.calls.call_count == 1


@pytest.mark.asyncio
async def test_fetch_500_retry():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as respx_mock:
            respx_mock.get("/error").mock(return_value=httpx.Response(500))
            result = await fetch_from_source(
                client,
                "https://example.com/error",
                max_retries=2,
                retry_delay=0.01,
                app_settings=_mocked_settings(),
            )

            assert not result.success
            assert respx_mock.calls.call_count == 2
