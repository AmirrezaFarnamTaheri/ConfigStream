import pytest
import httpx
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from configstream.fetcher import (
    fetch_from_source,
    fetch_multiple_sources,
    MAX_RESPONSE_SIZE,
)
from configstream.fetcher_core.models import FetchResult
from configstream.fetcher_core.utils import parse_retry_after as _parse_retry_after

from configstream.config import AppSettings
from configstream.security.rate_limiter import RateLimiter


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

    # Setup async iterator for text
    async def async_iter():
        yield "data"

    mock_response.aiter_text = lambda: async_iter()

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
    client = AsyncMock(spec=httpx.AsyncClient)
    rate_limiter = MagicMock(spec=RateLimiter)
    # First call not allowed, second allowed
    rate_limiter.is_allowed.side_effect = [False, True]
    rate_limiter.get_wait_time.return_value = 0.01

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # Ensure successful fetch after waiting
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {}

        async def async_iter():
            yield "data"

        mock_response.aiter_text = lambda: async_iter()
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
    breaker.is_open = True
    breaker_manager.get_breaker.return_value = breaker

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
    mock_response.headers = {"Content-Length": str(MAX_RESPONSE_SIZE + 100)}

    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__.return_value = mock_response
    client.stream.return_value = mock_stream_ctx

    result = await fetch_from_source(client, "http://valid.com", max_retries=1)

    assert not result.success
    assert "Response too large" in result.error


@pytest.mark.asyncio
async def test_fetch_from_source_too_large_stream():
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {}

    # Generate large chunks
    async def async_iter():
        yield "a" * (MAX_RESPONSE_SIZE + 100)

    mock_response.aiter_text = lambda: async_iter()

    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__.return_value = mock_response
    client.stream.return_value = mock_stream_ctx

    result = await fetch_from_source(client, "http://valid.com", max_retries=1)

    assert not result.success
    assert "Response too large" in result.error


@pytest.mark.asyncio
async def test_fetch_from_source_jitter_warning(caplog):
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {}

    async def async_gen():
        yield "data"

    mock_response.aiter_text = lambda: async_gen()

    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__.return_value = mock_response
    client.stream.return_value = mock_stream_ctx

    tracker = MagicMock()
    tracker.get_timeout.return_value = 10.0
    tracker.get_jitter.return_value = 3.0  # High jitter

    with patch("configstream.fetcher.logger") as mock_logger:
        await fetch_from_source(client, "http://valid.com", timeout_tracker=tracker)
        assert mock_logger.warning.called
        assert "High Jitter" in mock_logger.warning.call_args[0][0]


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
    with patch("configstream.fetcher.fetch_from_source") as mock_single:
        mock_single.return_value = FetchResult(True, "src1")

        # Implicit client=None
        results = await fetch_multiple_sources(["http://src1.com"], max_concurrent=1)

        assert len(results) == 1
        assert results["http://src1.com"].success


@pytest.mark.asyncio
async def test_fetch_multiple_sources_with_explicit_client():
    client = AsyncMock(spec=httpx.AsyncClient)
    with patch("configstream.fetcher.fetch_from_source") as mock_single:
        mock_single.return_value = FetchResult(True, "src1")

        results = await fetch_multiple_sources(["http://src1.com"], client=client)

        assert len(results) == 1
