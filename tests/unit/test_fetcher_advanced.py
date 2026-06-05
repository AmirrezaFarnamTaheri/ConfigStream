# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import patch, MagicMock
import httpx
from configstream.pipeline.fetcher import fetch_from_source
from configstream.config import AppSettings
from configstream.circuit_breaker import CircuitBreakerManager


def mocked_fetch_settings(**kwargs):
    settings = AppSettings(**kwargs)
    settings.FETCH_VALIDATE_DNS = False
    return settings


# Helper to mock the stream context manager
class MockStreamResponse:
    def __init__(self, status_code, text="", headers=None):
        self.status_code = status_code
        self.text_content = text
        self.headers = headers or {}
        self.http_version = "HTTP/1.1"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise httpx.HTTPStatusError(
                f"Error {self.status_code}", request=None, response=self
            )

    async def aiter_bytes(self):
        if isinstance(self.text_content, str):
            yield self.text_content.encode("utf-8")
        else:
            yield self.text_content


@pytest.mark.asyncio
async def test_fetch_success():
    # Mock stream instead of get
    with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:
        mock_stream.return_value = MockStreamResponse(200, "ok")

        client = httpx.AsyncClient()
        res = await fetch_from_source(
            client, "http://ok.com", app_settings=mocked_fetch_settings()
        )
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
        res = await fetch_from_source(
            client,
            "http://retry.com",
            max_retries=2,
            app_settings=mocked_fetch_settings(),
        )

        assert res.success
        assert res.content == "ok"
        assert mock_stream.call_count == 2


@pytest.mark.asyncio
async def test_fetch_circuit_breaker_open():
    breaker_manager = CircuitBreakerManager()
    host = "broken.com"
    # Trip the breaker
    breaker = await breaker_manager.get_breaker(host)
    for _ in range(10):
        await breaker.record_failure()

    assert await breaker.is_open()

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
    # We verify that it falls back to standard stream even if hedging is enabled.

    with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:
        mock_stream.return_value = MockStreamResponse(200, "streamed_content")

        settings = mocked_fetch_settings(HEDGING_ENABLED=True, HEDGE_AFTER_MS=100)
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
    # The error message depends on httpx handling or our validation
    assert res.error is not None


@pytest.mark.asyncio
async def test_fetch_404_trips_breaker_and_skips_subsequent_calls():
    breaker_manager = CircuitBreakerManager(failure_threshold=2, recovery_timeout=60)
    host = "dead.example"

    with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:
        mock_stream.return_value = MockStreamResponse(404, "")
        client = httpx.AsyncClient()

        res1 = await fetch_from_source(
            client,
            f"http://{host}/missing-1",
            max_retries=1,
            app_settings=mocked_fetch_settings(CIRCUIT_BREAKER_ENABLED=True),
            breaker_manager=breaker_manager,
        )
        res2 = await fetch_from_source(
            client,
            f"http://{host}/missing-2",
            max_retries=1,
            app_settings=mocked_fetch_settings(CIRCUIT_BREAKER_ENABLED=True),
            breaker_manager=breaker_manager,
        )
        res3 = await fetch_from_source(
            client,
            f"http://{host}/missing-3",
            max_retries=1,
            app_settings=mocked_fetch_settings(CIRCUIT_BREAKER_ENABLED=True),
            breaker_manager=breaker_manager,
        )

    assert not res1.success and "Permanent Error: 404" in (res1.error or "")
    assert not res2.success and "Permanent Error: 404" in (res2.error or "")
    assert not res3.success and "Circuit Breaker Open" in (res3.error or "")
    assert mock_stream.call_count == 2
