# SPDX-License-Identifier: AGPL-3.0-or-later
import httpx
import pytest
import respx

from configstream.config import AppSettings
from configstream.pipeline.fetcher import _retry_backoff, fetch_from_source


def _mocked_settings() -> AppSettings:
    """Return fetch settings that keep retry tests independent of live DNS."""

    settings = AppSettings()
    settings.FETCH_VALIDATE_DNS = False
    return settings


def test_retry_backoff_is_bounded_exponential_full_jitter() -> None:
    """Keep retry jitter within its exponential ceiling and configured cap."""

    for attempt in range(1, 8):
        delay = _retry_backoff(1.0, attempt, cap=30.0)
        assert 0.0 <= delay <= min(30.0, 2**attempt)
    assert _retry_backoff(0.0, 10) == 0.0


@pytest.mark.asyncio
async def test_fetch_404_abort():
    """Treat HTTP 404 as permanent and avoid redundant retries."""

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
    """Treat HTTP 410 as permanent and avoid redundant retries."""

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
    """Retry transient HTTP 500 responses up to the configured attempt limit."""

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
