import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from configstream.hedged_requests import hedged_get


@pytest.mark.asyncio
async def test_hedged_request_success_first():
    mock_client = AsyncMock()
    mock_response = MagicMock(status_code=200, text="Success")
    mock_client.get.return_value = mock_response

    # Signature: client, url, timeout, hedge_after, headers
    response = await hedged_get(
        mock_client, "http://example.com", timeout=5.0, hedge_after=0.1, headers={}
    )

    assert response[0] is True  # Success boolean
    assert response[1].status_code == 200


@pytest.mark.asyncio
async def test_hedged_request_all_fail():
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("Connection Error")

    success, result = await hedged_get(
        mock_client, "http://example.com", timeout=0.1, hedge_after=0.01, headers={}
    )
    assert success is False
    assert isinstance(result, Exception)


@pytest.mark.asyncio
async def test_hedged_request_second_succeeds():
    mock_client = AsyncMock()

    async def side_effect(*args, **kwargs):
        # We need to delay the first call, but let second pass?
        # Since it's the same client, we need state.
        if not hasattr(side_effect, "calls"):
            side_effect.calls = 0
        side_effect.calls += 1

        if side_effect.calls == 1:
            await asyncio.sleep(0.2)  # Longer than hedge_after (0.05)
            return MagicMock(status_code=500)
        return MagicMock(status_code=200, text="Fast")

    mock_client.get.side_effect = side_effect

    success, result = await hedged_get(
        mock_client, "http://example.com", timeout=1.0, hedge_after=0.05, headers={}
    )
    assert success is True
    assert result.text == "Fast"


@pytest.mark.asyncio
async def test_hedged_request_cancellation_check():
    """Verify that the slow task is cancelled when another succeeds."""
    mock_client = AsyncMock()

    # We will use an Event to track if the slow task was cancelled
    slow_task_cancelled = asyncio.Event()

    async def side_effect(*args, **kwargs):
        if not hasattr(side_effect, "calls"):
            side_effect.calls = 0
        side_effect.calls += 1

        if side_effect.calls == 1:
            # First call is slow
            try:
                await asyncio.sleep(2.0)
                return MagicMock(status_code=200, text="Slow")
            except asyncio.CancelledError:
                slow_task_cancelled.set()
                raise
        else:
            # Second call is fast
            return MagicMock(status_code=200, text="Fast")

    mock_client.get.side_effect = side_effect

    # Hedge after 0.05s, first task sleeps 2.0s
    success, result = await hedged_get(
        mock_client, "http://example.com", timeout=1.0, hedge_after=0.05, headers={}
    )

    assert success is True
    assert result.text == "Fast"

    # Check if the slow task was cancelled
    # We might need to wait a tiny bit for the callback to fire
    try:
        await asyncio.wait_for(slow_task_cancelled.wait(), timeout=0.5)
    except asyncio.TimeoutError:
        pytest.fail("The slow task was not cancelled properly!")
