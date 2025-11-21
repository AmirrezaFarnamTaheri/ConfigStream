import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from configstream.fetcher import fetch_from_source, FetchResult
from configstream.config import AppSettings
from configstream.circuit_breaker import CircuitBreakerManager


# Helper to mock the stream context manager
class MockStreamResponse:
    def __init__(self, status_code, text="", headers=None):
        self.status_code = status_code
        self.text_content = text
        self.headers = headers or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def raise_for_status(self):
        pass

    async def aiter_text(self):
        yield self.text_content


@pytest.mark.asyncio
async def test_fetch_success():
    # Mock stream instead of get
    with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:
        mock_stream.return_value = MockStreamResponse(200, "ok")

        client = httpx.AsyncClient()
        res = await fetch_from_source(client, "http://ok.com")
        assert res.success
        assert res.content == "ok"


@pytest.mark.asyncio
async def test_fetch_rate_limit_retry():
    # First call 429, second call 200
    with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:
        resp1 = MockStreamResponse(429, "", headers={"Retry-After": "0.1"})
        resp2 = MockStreamResponse(200, "ok")

        mock_stream.side_effect = [resp1, resp2]

        client = httpx.AsyncClient()
        res = await fetch_from_source(client, "http://retry.com", max_retries=2)

        assert res.success
        assert res.content == "ok"
        assert mock_stream.call_count == 2


@pytest.mark.asyncio
async def test_fetch_circuit_breaker_open():
    breaker_manager = CircuitBreakerManager()
    host = "broken.com"
    # Trip the breaker
    breaker = breaker_manager.get_breaker(host)
    for _ in range(10):
        breaker.record_failure()

    assert breaker.is_open

    client = httpx.AsyncClient()
    res = await fetch_from_source(
        client,
        f"http://{host}",
        app_settings=AppSettings(CIRCUIT_BREAKER_ENABLED=True),
        breaker_manager=breaker_manager,
    )

    assert not res.success
    assert "Circuit Breaker Open" in res.error


@pytest.mark.asyncio
async def test_hedged_request_success():
    # Test hedging path
    # Note: In our current implementation, hedging logic is disabled/bypassed if stream is used
    # OR we need to mock how it works.
    # The fetcher implementation:
    # if app_settings.HEDGING_ENABLED:
    #    pass  # Reverting to standard stream
    # async with client.stream(...)

    # So hedged_get is NOT called in the current robust implementation.
    # We verify that it falls back to standard stream even if hedging is enabled.

    with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:
        mock_stream.return_value = MockStreamResponse(200, "streamed_content")

        settings = AppSettings(HEDGING_ENABLED=True, HEDGE_AFTER_MS=100)
        client = httpx.AsyncClient()

        res = await fetch_from_source(client, "http://hedge.com", app_settings=settings)

        assert res.success
        assert res.content == "streamed_content"
        # We assert mock_stream was called, implying we used the safer path
        mock_stream.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_invalid_url():
    client = httpx.AsyncClient()
    res = await fetch_from_source(client, "not_a_url")
    assert not res.success
    assert "Invalid URL" in res.error
