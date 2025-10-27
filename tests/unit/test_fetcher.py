import pytest
from unittest.mock import patch, AsyncMock
from configstream.fetcher import (
    fetch_from_source,
    _parse_retry_after_header,
    fetch_multiple_sources,
    FetchResult,
)
import httpx
import asyncio
from datetime import datetime, timezone, timedelta


@pytest.fixture
def mock_async_client():
    mock = AsyncMock()
    mock.get.return_value = AsyncMock(
        status_code=200,
        text="vmess://config1\nss://config2",
        headers={"Content-Type": "text/plain"},
    )
    return mock


@pytest.mark.asyncio
async def test_fetch_from_source_server_error(mock_async_client):
    mock_async_client.get.side_effect = [
        AsyncMock(status_code=500),
        AsyncMock(status_code=502),
        httpx.ReadError("test error"),
    ]
    result = await fetch_from_source(
        mock_async_client, "http://example.com", max_retries=3, retry_delay=0.01
    )
    assert not result.success
    assert "test error" in result.error
    assert mock_async_client.get.call_count == 3


@pytest.mark.asyncio
async def test_fetch_from_source_html_content_type(mock_async_client, caplog):
    mock_async_client.get.return_value.headers = {"Content-Type": "text/html"}
    await fetch_from_source(mock_async_client, "http://example.com")
    assert "Unexpected content type for http://example.com: text/html" in caplog.text


@pytest.mark.asyncio
async def test_fetch_from_source_rate_limit_with_retry_after_header(mock_async_client):
    mock_async_client.get.side_effect = [
        AsyncMock(status_code=429, headers={"Retry-After": "0.1"}),
        AsyncMock(status_code=200, text="ss://config"),
    ]
    result = await fetch_from_source(
        mock_async_client, "http://example.com", max_retries=2, retry_delay=0.01
    )
    assert result.success
    assert len(result.configs) == 1
    assert mock_async_client.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_from_source_timeout_exception(mock_async_client):
    mock_async_client.get.side_effect = httpx.TimeoutException("Timeout")
    result = await fetch_from_source(mock_async_client, "http://example.com", max_retries=1)
    assert not result.success
    assert "Timeout" in result.error


@pytest.mark.asyncio
async def test_fetch_from_source_invalid_url():
    result = await fetch_from_source(AsyncMock(), "invalid-url")
    assert not result.success
    assert "Invalid URL" in result.error


def test_parse_retry_after_header():
    assert _parse_retry_after_header(None) is None
    assert _parse_retry_after_header("  ") is None
    assert _parse_retry_after_header("120") == 120.0

    future_time = datetime.now(timezone.utc) + timedelta(seconds=60)
    http_date = future_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Mocking datetime.now can be tricky. Instead, we check if it's within a range.
    parsed_delta = _parse_retry_after_header(http_date)
    assert parsed_delta is not None
    assert 59 < parsed_delta <= 60

    assert _parse_retry_after_header("invalid-date") is None


@pytest.mark.asyncio
async def test_fetch_multiple_sources_unhandled_exception():
    sources = ["http://example.com/source1", "http://example.com/source2"]

    async def side_effect(client, source, *args, **kwargs):
        if "source1" in source:
            raise ValueError("Unhandled test exception")
        return FetchResult(source, ["ss://config"], True)

    with patch("configstream.fetcher.fetch_from_source", side_effect=side_effect):
        results = await fetch_multiple_sources(sources)

    assert len(results) == 2
    assert not results["http://example.com/source1"].success
    assert "Unhandled test exception" in results["http://example.com/source1"].error
    assert results["http://example.com/source2"].success
    assert len(results["http://example.com/source2"].configs) == 1
