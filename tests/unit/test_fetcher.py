# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import httpx
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from configstream.fetcher import fetch_from_source
from configstream.fetcher import fetch_multiple_sources
from configstream.fetcher_worker import FetchResult
from configstream.fetcher_worker import parse_retry_after as _parse_retry_after

from configstream.config import AppSettings


def test_parse_retry_after():
    # Test integer
    assert _parse_retry_after("60") == 60.0

    # Test date
    future = datetime.now(timezone.utc) + timedelta(seconds=120)
    date_str = future.strftime("%a, %d %b %Y %H:%M:%S GMT")
    parsed = _parse_retry_after(date_str)
    assert parsed is not None
    assert 118 < parsed < 122  # Allow small delta

    # Test invalid
    assert _parse_retry_after("invalid") is None
    assert _parse_retry_after(None) is None


@pytest.mark.asyncio
async def test_fetch_from_source_invalid_url():
    client = AsyncMock(spec=httpx.AsyncClient)
    result = await fetch_from_source(client, "invalid-url")
    assert not result.success
    assert "Invalid URL" in result.error


@pytest.mark.asyncio
async def test_fetch_from_source_success():
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {}

    # Setup async iterator for bytes
    async def async_iter():
        yield b"data"

    mock_response.aiter_bytes = lambda: async_iter()

    # Context manager for client.stream
    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__.return_value = mock_response
    client.stream.return_value = mock_stream_ctx

    result = await fetch_from_source(client, "http://valid.com")

    assert result.success
    assert result.content == "data"
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_fetch_from_source_rate_limit():
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = AsyncMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "0.1"}

    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__.return_value = mock_response
    client.stream.return_value = mock_stream_ctx

    # Should retry. We mock sleep to be fast.
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await fetch_from_source(client, "http://valid.com", max_retries=2)

    # It fails after retries if it keeps returning 429
    assert not result.success
    assert "Rate limited" in result.error
    assert mock_sleep.call_count > 0


@pytest.mark.asyncio
async def test_fetch_from_source_rate_limiter_precheck():
    # Backward compatibility test - ensure it doesn't crash if passed
    # but actual logic is now skipped or simplified if RateLimiter is removed.
    # If RateLimiter class is gone, we can mock a generic object with the same interface.
    client = AsyncMock(spec=httpx.AsyncClient)
    rate_limiter = MagicMock()
    # First call not allowed, second allowed (async methods)
    rate_limiter.is_allowed = AsyncMock(side_effect=[False, True])
    rate_limiter.get_wait_time = AsyncMock(return_value=0.01)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # Ensure successful fetch after waiting
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {}

        async def async_iter():
            yield b"data"

        mock_response.aiter_bytes = lambda: async_iter()
        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__.return_value = mock_response
        client.stream.return_value = mock_stream_ctx

        result = await fetch_from_source(
            client, "http://valid.com", rate_limiter=rate_limiter
        )

    assert result.success
    assert mock_sleep.called


@pytest.mark.asyncio
async def test_fetch_from_source_circuit_breaker():
    client = AsyncMock(spec=httpx.AsyncClient)
    breaker_manager = MagicMock()
    breaker = MagicMock()
    breaker.is_open = AsyncMock(return_value=True)
    breaker_manager.get_breaker = AsyncMock(return_value=breaker)

    app_settings = AppSettings()
    app_settings.CIRCUIT_BREAKER_ENABLED = True

    result = await fetch_from_source(
        client,
        "http://valid.com",
        breaker_manager=breaker_manager,
        app_settings=app_settings,
    )

    assert not result.success
    assert "Circuit Breaker Open" in result.error


@pytest.mark.asyncio
async def test_fetch_from_source_too_large_header():
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = AsyncMock()
    mock_response.status_code = 200
    app_settings = AppSettings()
    app_settings.MAX_RESPONSE_SIZE = 100
    mock_response.headers = {
        "Content-Length": str(app_settings.MAX_RESPONSE_SIZE + 100)
    }

    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__.return_value = mock_response
    client.stream.return_value = mock_stream_ctx

    result = await fetch_from_source(
        client, "http://valid.com", max_retries=1, app_settings=app_settings
    )

    assert not result.success
    assert "Response too large" in result.error


@pytest.mark.asyncio
async def test_fetch_from_source_too_large_stream():
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    app_settings = AppSettings()
    app_settings.MAX_RESPONSE_SIZE = 100

    # Generate large chunks
    async def async_iter():
        yield b"a" * (app_settings.MAX_RESPONSE_SIZE + 100)

    mock_response.aiter_bytes = lambda: async_iter()

    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__.return_value = mock_response
    client.stream.return_value = mock_stream_ctx

    result = await fetch_from_source(
        client, "http://valid.com", max_retries=1, app_settings=app_settings
    )

    assert not result.success
    assert "Response too large" in result.error


@pytest.mark.asyncio
async def test_fetch_from_source_jitter_warning(caplog):
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {}

    async def async_gen():
        yield b"data"

    mock_response.aiter_bytes = lambda: async_gen()

    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__.return_value = mock_response
    client.stream.return_value = mock_stream_ctx

    tracker = MagicMock()
    tracker.get_timeout = MagicMock(return_value=10.0)
    tracker.record = AsyncMock()
    tracker.get_jitter = AsyncMock(return_value=3.0)  # High jitter

    # Patch correct logger location after refactor
    with patch("configstream.fetcher.logger") as mock_logger:
        await fetch_from_source(client, "http://valid.com", timeout_tracker=tracker)
        # Check if any call to info contains "High Jitter"
        assert any("High Jitter" in str(call) for call in mock_logger.info.mock_calls)


@pytest.mark.asyncio
async def test_fetch_from_source_unexpected_exception():
    client = AsyncMock(spec=httpx.AsyncClient)
    # client.stream raises generic Exception
    client.stream.side_effect = Exception("Boom")

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await fetch_from_source(client, "http://valid.com", max_retries=2)

    assert not result.success
    assert "Max retries exceeded" in result.error
    assert "Boom" in result.error
    assert mock_sleep.call_count > 0


@pytest.mark.asyncio
async def test_fetch_multiple_sources_integration():
    # Integration test mocking minimal internals
    # Patch correct location
    with patch("configstream.fetcher.fetch_from_source") as mock_single:
        mock_single.return_value = FetchResult(True, "src1")

        # Implicit client=None
        results = await fetch_multiple_sources(["http://src1.com"], max_concurrent=1)

        assert len(results) == 1
        assert results["http://src1.com"].success


@pytest.mark.asyncio
async def test_fetch_multiple_sources_with_explicit_client():
    client = AsyncMock(spec=httpx.AsyncClient)
    # Patch correct location
    with patch("configstream.fetcher.fetch_from_source") as mock_single:
        mock_single.return_value = FetchResult(True, "src1")

        results = await fetch_multiple_sources(["http://src1.com"], client=client)

        assert len(results) == 1
