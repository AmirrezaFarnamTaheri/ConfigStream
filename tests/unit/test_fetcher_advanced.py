import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from configstream.fetcher import fetch_from_source, FetchResult
from configstream.config import AppSettings
from configstream.circuit_breaker import CircuitBreakerManager


@pytest.mark.asyncio
async def test_fetch_success():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"
        mock_get.return_value = mock_resp

        client = httpx.AsyncClient()
        res = await fetch_from_source(client, "http://ok.com")
        assert res.success
        assert res.content == "ok"


@pytest.mark.asyncio
async def test_fetch_rate_limit_retry():
    # First call 429, second call 200
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        resp1 = MagicMock()
        resp1.status_code = 429
        resp1.headers = {"Retry-After": "0.1"}

        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.text = "ok"

        mock_get.side_effect = [resp1, resp2]

        client = httpx.AsyncClient()
        res = await fetch_from_source(client, "http://retry.com", max_retries=2)

        assert res.success
        assert res.content == "ok"
        assert mock_get.call_count == 2


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
    with patch("configstream.fetcher.hedged_get", new_callable=AsyncMock) as mock_hedge:
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "hedged"
        mock_hedge.return_value = (True, resp)

        settings = AppSettings(HEDGING_ENABLED=True, HEDGE_AFTER_MS=100)
        client = httpx.AsyncClient()

        res = await fetch_from_source(client, "http://hedge.com", app_settings=settings)

        assert res.success
        assert res.content == "hedged"
        mock_hedge.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_invalid_url():
    client = httpx.AsyncClient()
    res = await fetch_from_source(client, "not_a_url")
    assert not res.success
    assert "Invalid URL" in res.error
