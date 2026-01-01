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

    # We use a task tracker to ensure tasks are properly cancelled
    active_tasks = set()

    async def side_effect(*args, **kwargs):
        task = asyncio.current_task()
        active_tasks.add(task)
        try:
            if not hasattr(side_effect, "calls"):
                side_effect.calls = 0
            side_effect.calls += 1

            if side_effect.calls == 1:
                # First request hangs/sleeps
                await asyncio.sleep(0.5)
                return MagicMock(status_code=500)
            # Second request returns fast
            return MagicMock(status_code=200, text="Fast")
        finally:
            active_tasks.discard(task)

    mock_client.get.side_effect = side_effect

    success, result = await hedged_get(
        mock_client, "http://example.com", timeout=1.0, hedge_after=0.05, headers={}
    )
    assert success is True
    assert result.text == "Fast"

    # Allow a small moment for cancellation callbacks to fire
    await asyncio.sleep(0.01)

    # Verify that the slow first task was cancelled (not in active_tasks)
    # Note: hedged_get uses asyncio.gather(return_exceptions=True) which waits for tasks to finish/cancel.
    # If the task was cancelled, it should exit.
    # Our side_effect 'finally' block discards the task.
    assert len(active_tasks) == 0
