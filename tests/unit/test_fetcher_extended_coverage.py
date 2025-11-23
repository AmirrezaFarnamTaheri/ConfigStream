
import pytest
import httpx
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from src.configstream.fetcher import (
    FetchResult,
    RateLimitError,
    _parse_retry_after,
    fetch_from_source,
    fetch_multiple_sources,
)
from src.configstream.config import AppSettings

# --- FetchResult ---
def test_fetch_result_to_dict():
    res = FetchResult(True, "src", "content", status_code=200, response_time=0.1)
    d = res.to_dict()
    assert d["success"] is True
    assert d["source"] == "src"
    assert d["content_length"] == 7
    assert d["status_code"] == 200

# --- _parse_retry_after ---
def test_parse_retry_after_seconds():
    assert _parse_retry_after("10") == 10.0

def test_parse_retry_after_date():
    future = datetime.now(timezone.utc) + timedelta(seconds=60)
    http_date = future.strftime("%a, %d %b %Y %H:%M:%S GMT")
    seconds = _parse_retry_after(http_date)
    assert 50 < seconds < 70

def test_parse_retry_after_invalid():
    assert _parse_retry_after(None) is None
    assert _parse_retry_after("invalid") is None

# --- fetch_from_source ---

@pytest.mark.asyncio
async def test_fetch_invalid_url():
    async with httpx.AsyncClient() as client:
        res = await fetch_from_source(client, "invalid-url")
        assert res.success is False
        assert "Invalid URL" in res.error

@pytest.mark.asyncio
async def test_fetch_success():
    with patch("httpx.AsyncClient.stream") as mock_stream:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.headers = {}

        # Mock aiter_text
        # aiter_text is called as a method that returns an async iterator.
        # But AsyncMock makes aiter_text return an AsyncMock.
        # We need aiter_text() to return an async iterator.

        async def text_gen():
            yield "content"

        # mock_resp.aiter_text needs to be a callable that returns text_gen()
        mock_resp.aiter_text.side_effect = text_gen

        mock_stream.return_value.__aenter__.return_value = mock_resp

        async with httpx.AsyncClient() as client:
            res = await fetch_from_source(client, "http://example.com")
            assert res.success is True
            assert res.content == "content"

@pytest.mark.asyncio
async def test_fetch_rate_limit_error():
    with patch("httpx.AsyncClient.stream") as mock_stream:
        mock_resp = AsyncMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"Retry-After": "1"}
        mock_stream.return_value.__aenter__.return_value = mock_resp

        async with httpx.AsyncClient() as client:
            # Should retry but eventually fail if max_retries exceeded (or mock always returns 429)
            res = await fetch_from_source(client, "http://example.com", max_retries=2, retry_delay=0.1)
            assert res.success is False
            assert "Rate limited" in res.error

@pytest.mark.asyncio
async def test_fetch_too_large_header():
    with patch("httpx.AsyncClient.stream") as mock_stream:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Length": "999999999"}
        mock_stream.return_value.__aenter__.return_value = mock_resp

        async with httpx.AsyncClient() as client:
            res = await fetch_from_source(client, "http://example.com")
            assert res.success is False
            assert "Response too large" in res.error

@pytest.mark.asyncio
async def test_fetch_too_large_stream():
    with patch("httpx.AsyncClient.stream") as mock_stream, \
         patch("src.configstream.fetcher.MAX_RESPONSE_SIZE", 5): # Small limit
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.headers = {}

        async def text_gen():
            yield "123456"
        mock_resp.aiter_text.side_effect = text_gen

        mock_stream.return_value.__aenter__.return_value = mock_resp

        async with httpx.AsyncClient() as client:
            res = await fetch_from_source(client, "http://example.com")
            assert res.success is False
            assert "Response too large" in res.error

# --- fetch_multiple_sources ---

@pytest.mark.asyncio
async def test_fetch_multiple_sources():
    with patch("src.configstream.fetcher.fetch_from_source") as mock_fetch:
        mock_fetch.return_value = FetchResult(True, "s1")

        results = await fetch_multiple_sources(["http://s1", "http://s2"])
        assert len(results) == 2
        assert results["http://s1"].success is True
