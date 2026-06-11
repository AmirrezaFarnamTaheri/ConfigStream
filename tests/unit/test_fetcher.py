# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import pytest
import httpx
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from configstream.pipeline.fetcher import fetch_from_source
from configstream.pipeline.fetcher import fetch_multiple_sources
from configstream.fetcher_worker import FetchResult
from configstream.fetcher_worker import parse_retry_after as _parse_retry_after

from configstream.config import AppSettings


def _mocked_fetch_settings() -> AppSettings:
    settings = AppSettings()
    settings.FETCH_VALIDATE_DNS = False
    return settings


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
async def test_fetch_from_source_rejects_private_source_url():
    client = AsyncMock(spec=httpx.AsyncClient)
    result = await fetch_from_source(client, "http://127.0.0.1/sub")

    assert result.success is False
    assert "non-global" in result.error
    client.stream.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_from_source_success():
    client = AsyncMock(spec=httpx.AsyncClient)
    app_settings = AppSettings()
    app_settings.FETCH_VALIDATE_DNS = False
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

    result = await fetch_from_source(
        client, "http://valid.com", app_settings=app_settings
    )

    assert result.success
    assert result.content == "data"
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_fetch_from_source_rate_limit():
    client = AsyncMock(spec=httpx.AsyncClient)
    app_settings = AppSettings()
    app_settings.FETCH_VALIDATE_DNS = False
    mock_response = AsyncMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "0.1"}

    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__.return_value = mock_response
    client.stream.return_value = mock_stream_ctx

    # Should retry. We mock sleep to be fast.
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await fetch_from_source(
            client, "http://valid.com", max_retries=2, app_settings=app_settings
        )

    # It fails after retries if it keeps returning 429
    assert not result.success
    assert "Rate limited" in result.error
    assert mock_sleep.call_count > 0


@pytest.mark.asyncio
async def test_fetch_from_source_follows_safe_redirect(respx_mock):
    source = "https://example.com/start"
    target = "https://example.org/final"
    respx_mock.get(source).mock(
        return_value=httpx.Response(302, headers={"Location": target})
    )
    respx_mock.get(target).mock(return_value=httpx.Response(200, text="redirected"))

    async with httpx.AsyncClient() as client:
        result = await fetch_from_source(client, source)

    assert result.success is True
    assert result.content == "redirected"


@pytest.mark.asyncio
async def test_fetch_from_source_rejects_private_redirect(respx_mock):
    source = "https://example.com/start"
    respx_mock.get(source).mock(
        return_value=httpx.Response(
            302,
            headers={"Location": "http://127.0.0.1/admin"},
        )
    )

    async with httpx.AsyncClient() as client:
        result = await fetch_from_source(client, source)

    assert result.success is False
    assert "Unsafe redirect target" in result.error


@pytest.mark.asyncio
async def test_fetch_from_source_rejects_private_dns_resolution():
    client = AsyncMock(spec=httpx.AsyncClient)

    async def fake_getaddrinfo(*args, **kwargs):
        return [
            (
                2,
                1,
                6,
                "",
                ("10.0.0.5", 443),
            )
        ]

    loop = asyncio.get_running_loop()
    with patch.object(loop, "getaddrinfo", side_effect=fake_getaddrinfo):
        result = await fetch_from_source(client, "https://safe-name.example/sub")

    assert result.success is False
    assert "resolves to a private or non-global address" in result.error
    client.stream.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_from_source_validates_redirect_dns_before_fetch(respx_mock):
    settings = AppSettings()
    source = "https://example.com/start"
    target = "https://safe-name.example/final"
    respx_mock.get(source).mock(
        return_value=httpx.Response(302, headers={"Location": target})
    )

    async def fake_getaddrinfo(host, *args, **kwargs):
        ip = "93.184.216.34" if host == "example.com" else "127.0.0.1"
        return [(2, 1, 6, "", (ip, 443))]

    loop = asyncio.get_running_loop()
    with patch.object(loop, "getaddrinfo", side_effect=fake_getaddrinfo):
        async with httpx.AsyncClient() as client:
            result = await fetch_from_source(
                client, source, app_settings=settings, max_retries=1
            )

    assert result.success is False
    assert "resolves to a private or non-global address" in result.error


@pytest.mark.asyncio
async def test_fetch_from_source_limits_redirect_depth(respx_mock):
    settings = AppSettings()
    settings.FETCH_MAX_REDIRECTS = 0
    source = "https://example.com/start"
    respx_mock.get(source).mock(
        return_value=httpx.Response(
            302,
            headers={"Location": "https://example.org/final"},
        )
    )

    async with httpx.AsyncClient() as client:
        result = await fetch_from_source(client, source, app_settings=settings)

    assert result.success is False
    assert result.error == "Too many redirects"


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

    app_settings = _mocked_fetch_settings()
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
            client,
            "http://valid.com",
            rate_limiter=rate_limiter,
            app_settings=app_settings,
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
    app_settings.FETCH_VALIDATE_DNS = False
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
    app_settings.FETCH_VALIDATE_DNS = False

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
    app_settings = _mocked_fetch_settings()
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
    with patch("configstream.pipeline.fetcher.logger") as mock_logger:
        await fetch_from_source(
            client,
            "http://valid.com",
            timeout_tracker=tracker,
            app_settings=app_settings,
        )
        # Check if any call to info contains "High Jitter"
        assert any("High Jitter" in str(call) for call in mock_logger.info.mock_calls)


@pytest.mark.asyncio
async def test_fetch_from_source_unexpected_exception():
    client = AsyncMock(spec=httpx.AsyncClient)
    app_settings = _mocked_fetch_settings()
    # client.stream raises generic Exception
    client.stream.side_effect = Exception("Boom")

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await fetch_from_source(
            client,
            "http://valid.com",
            max_retries=2,
            app_settings=app_settings,
        )

    assert not result.success
    assert "Max retries exceeded" in result.error
    assert "Boom" in result.error
    assert mock_sleep.call_count > 0


@pytest.mark.asyncio
async def test_fetch_multiple_sources_integration():
    # Integration test mocking minimal internals
    # Patch correct location
    with patch("configstream.pipeline.fetcher.fetch_from_source") as mock_single:
        mock_single.return_value = FetchResult(True, "src1")

        # Implicit client=None
        results = await fetch_multiple_sources(["http://src1.com"], max_concurrent=1)

        assert len(results) == 1
        assert results["http://src1.com"].success


@pytest.mark.asyncio
async def test_fetch_multiple_sources_with_explicit_client():
    client = AsyncMock(spec=httpx.AsyncClient)
    # Patch correct location
    with patch("configstream.pipeline.fetcher.fetch_from_source") as mock_single:
        mock_single.return_value = FetchResult(True, "src1")

        results = await fetch_multiple_sources(["http://src1.com"], client=client)

        assert len(results) == 1
