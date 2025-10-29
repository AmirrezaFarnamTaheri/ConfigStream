import asyncio
from unittest.mock import patch, AsyncMock

import pytest
import httpx
import respx

from configstream.fetcher import fetch_from_source, fetch_multiple_sources
from configstream.circuit_breaker import CircuitBreakerManager


@pytest.mark.asyncio
@respx.mock
async def test_adaptive_tuner_integration():
    """Test that the adaptive tuner ramps up and backs off with a real server."""
    url = "http://testserver/fast"
    respx.get(url).mock(return_value=httpx.Response(200, text="vmess://config"))

    with patch("configstream.config.AppSettings.AIMD_ENABLED", True):
        async with httpx.AsyncClient() as client:
            await fetch_multiple_sources([url] * 10, per_host_limit=2, client=client)


@pytest.mark.asyncio
@respx.mock
async def test_hedge_integration():
    """Test that hedging is triggered for slow responses."""
    url = "http://testserver/slow"
    hedge_after_ms = 50

    async def slow_side_effect(request):
        await asyncio.sleep((hedge_after_ms / 1000) * 2)
        return httpx.Response(200, text="vmess://config")

    respx.get(url).mock(side_effect=slow_side_effect)

    with patch("configstream.config.AppSettings.HEDGING_ENABLED", True), patch(
        "configstream.config.AppSettings.HEDGE_AFTER_MS", hedge_after_ms
    ), patch(
        "configstream.fetcher.hedged_get", new_callable=AsyncMock
    ) as mock_hedged_get:
        mock_hedged_get.return_value = (None, httpx.Response(200, text="vmess://config"))
        async with httpx.AsyncClient() as client:
            await fetch_from_source(client, url)
        mock_hedged_get.assert_called_once()


@pytest.mark.asyncio
@respx.mock
async def test_circuit_breaker_integration():
    """Test that the circuit breaker opens after multiple failures."""
    url = "http://testserver/fail"
    host = "testserver"
    respx.get(url).mock(return_value=httpx.Response(500))

    failure_threshold = 3
    recovery_timeout = 10

    with patch("configstream.config.AppSettings.CIRCUIT_BREAKER_ENABLED", True), patch(
        "configstream.config.AppSettings.CIRCUIT_TRIP_CONN_ERRORS", failure_threshold
    ), patch("configstream.config.AppSettings.CIRCUIT_OPEN_SEC", recovery_timeout):
        breaker_manager = CircuitBreakerManager(
            failure_threshold=failure_threshold, recovery_timeout=recovery_timeout
        )
        async with httpx.AsyncClient() as client:
            for _ in range(failure_threshold):
                await fetch_from_source(
                    client, url, breaker_manager=breaker_manager, max_retries=1
                )
            breaker = breaker_manager.get_breaker(host)
            assert breaker.is_open
            result = await fetch_from_source(
                client, url, breaker_manager=breaker_manager, max_retries=1
            )
            assert result.error == "Circuit breaker open"
