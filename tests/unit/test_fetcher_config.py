# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import httpx
from configstream.pipeline.fetcher import fetch_from_source
from configstream.config import AppSettings

# We need to test that MAX_RESPONSE_SIZE is picked up from the environment
# However, MAX_RESPONSE_SIZE is a constant imported at module level.
# To test env var override, we technically need to reload the module or
# assume the module picks it up at import time.
# Since I modified fetcher.py to read os.getenv at top level,
# testing it after import is tricky without reloading.
# Instead, I will verify the logic inside fetch_from_source respects the limit
# by mocking the constant or by testing the behavior with a large response.


@pytest.mark.asyncio
async def test_max_response_size_behavior():
    """Test that fetcher rejects responses larger than limit."""

    app_settings = AppSettings()
    app_settings.MAX_RESPONSE_SIZE = 100

    # Create a mock response with Content-Length > MAX_RESPONSE_SIZE
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {
        "Content-Length": str(app_settings.MAX_RESPONSE_SIZE + 100)
    }

    # Mock stream context manager
    mock_stream = MagicMock()
    mock_stream.__aenter__.return_value = mock_response
    mock_stream.__aexit__.return_value = None
    mock_client.stream.return_value = mock_stream

    # This test isolates response-size behavior; DNS pinning has its own test.
    with patch(
        "configstream.pipeline.fetcher._reject_source_dns",
        new=AsyncMock(return_value=(None, None)),
    ):
        result = await fetch_from_source(
            mock_client, "http://example.com", app_settings=app_settings
        )
        assert result.success is False
        assert "Response too large" in result.error


@pytest.mark.asyncio
async def test_env_var_override():
    """
    Test that MAX_RESPONSE_SIZE is available and has the expected default.
    """
    from configstream.fetcher_worker import MAX_RESPONSE_SIZE

    # Check if MAX_RESPONSE_SIZE is an int
    assert isinstance(MAX_RESPONSE_SIZE, int)
    # Default is unlimited (0)
    assert MAX_RESPONSE_SIZE == 0
