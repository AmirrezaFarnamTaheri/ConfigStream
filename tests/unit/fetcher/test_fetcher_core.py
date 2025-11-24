"""Tests for fetcher models and utils."""

from datetime import datetime, timedelta, timezone
from src.configstream.fetcher_core.utils import parse_retry_after
from src.configstream.fetcher_core.models import FetchResult, RateLimitError
from unittest.mock import patch


def test_fetch_result():
    res = FetchResult(True, "http://src", "content")
    assert res.success is True
    d = res.to_dict()
    assert d["source"] == "http://src"
    assert d["content_length"] == 7


def test_rate_limit_error():
    # Without retry after
    e = RateLimitError()
    assert "Rate limited." == str(e)

    # With retry after
    e = RateLimitError(retry_after=10.5)
    assert "Rate limited. Retry after 10.5s" == str(e)


def test_parse_retry_after():
    assert parse_retry_after(None) is None
    assert parse_retry_after("invalid") is None

    # Seconds
    assert parse_retry_after("10") == 10.0

    # Date
    now = datetime.now(timezone.utc)
    future = now + timedelta(seconds=60)
    # HTTP-date format
    date_str = future.strftime("%a, %d %b %Y %H:%M:%S GMT")

    parsed = parse_retry_after(date_str)
    assert parsed is not None
    # Tolerance for execution time
    assert 58.0 <= parsed <= 62.0

    # Exception case mocking
    with patch(
        "src.configstream.fetcher_core.utils.parsedate_to_datetime",
        side_effect=Exception("Boom"),
    ):
        assert parse_retry_after("date") is None
