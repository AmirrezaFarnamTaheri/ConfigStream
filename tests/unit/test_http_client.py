import pytest
from unittest.mock import patch, AsyncMock
from configstream.http_client import get_client


@pytest.mark.asyncio
async def test_get_client_http2_available():
    """Test that the client is configured for HTTP/2 when h2 is available."""
    with patch("configstream.http_client.HTTP2_AVAILABLE", True):
        with patch("configstream.http_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = AsyncMock()
            async with get_client():
                pass
            _, kwargs = mock_client.call_args
            assert kwargs.get("http2") is True


@pytest.mark.asyncio
async def test_get_client_http2_unavailable():
    """Test that the client falls back to HTTP/1.1 when h2 is not available."""
    with patch("configstream.http_client.HTTP2_AVAILABLE", False):
        with patch("configstream.http_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = AsyncMock()
            async with get_client():
                pass
            _, kwargs = mock_client.call_args
            assert kwargs.get("http2") is False
