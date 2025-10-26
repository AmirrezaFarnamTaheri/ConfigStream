import pytest
from unittest.mock import patch
from configstream.http_client import get_client


@pytest.mark.asyncio
async def test_get_client_http2_available():
    """Test that the client is configured for HTTP/2 when h2 is available."""
    with patch("configstream.http_client.HTTP2_AVAILABLE", True):
        async with get_client() as client:
            assert client._http2 is True


@pytest.mark.asyncio
async def test_get_client_http2_unavailable():
    """Test that the client falls back to HTTP/1.1 when h2 is not available."""
    with patch("configstream.http_client.HTTP2_AVAILABLE", False):
        async with get_client() as client:
            assert client._http2 is False
