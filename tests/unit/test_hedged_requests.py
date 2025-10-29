import asyncio
from unittest.mock import MagicMock, AsyncMock

import pytest
import httpx

from configstream.hedged_requests import hedged_get


@pytest.mark.asyncio
async def test_hedged_get_fast_response():
    """Test that hedged_get returns the first response if it's fast."""
    client = MagicMock()
    client.get = AsyncMock(return_value="fast_response")

    ok, response = await hedged_get(
        client, "http://fast.com", timeout=2, hedge_after=1, headers={}
    )
    assert ok
    assert response == "fast_response"
    client.get.assert_called_once()


@pytest.mark.asyncio
async def test_hedged_get_hedges_on_slow_response():
    """Test that a second request is made if the first is slow."""
    client = MagicMock()

    async def slow_then_fast(*args, **kwargs):
        if client.get.call_count == 1:
            await asyncio.sleep(2)
        return "fast_response"

    client.get = AsyncMock(side_effect=slow_then_fast)

    ok, response = await hedged_get(
        client, "http://slow.com", timeout=3, hedge_after=0.1, headers={}
    )
    assert ok
    assert response == "fast_response"
    assert client.get.call_count == 2


@pytest.mark.asyncio
async def test_hedged_get_returns_first_completed():
    """Test that the fastest of the two requests is returned."""
    client = MagicMock()

    async def side_effect(*args, **kwargs):
        if client.get.call_count == 1:
            await asyncio.sleep(0.2)
            return "slow_response"
        else:
            await asyncio.sleep(0.1)
            return "fast_response"

    client.get = AsyncMock(side_effect=side_effect)

    ok, response = await hedged_get(
        client, "http://race.com", timeout=2, hedge_after=0.05, headers={}
    )
    assert ok
    assert response == "fast_response"


@pytest.mark.asyncio
async def test_hedged_get_failure():
    """Test that hedged_get raises an exception on failure."""
    client = MagicMock()
    client.get = AsyncMock(side_effect=httpx.ReadError("test error"))

    with pytest.raises(httpx.ReadError):
        await hedged_get(client, "http://fail.com", timeout=2, hedge_after=1, headers={})


@pytest.mark.asyncio
async def test_hedged_get_timeout():
    """Test that hedged_get returns None on timeout."""
    client = MagicMock()

    async def slow_response(*args, **kwargs):
        await asyncio.sleep(2)
        return "slow_response"

    client.get = AsyncMock(side_effect=slow_response)

    ok, response = await hedged_get(
        client, "http://timeout.com", timeout=0.1, hedge_after=0.05, headers={}
    )
    assert not ok
    assert response is None
