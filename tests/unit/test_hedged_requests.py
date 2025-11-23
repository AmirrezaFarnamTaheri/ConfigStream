import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
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
