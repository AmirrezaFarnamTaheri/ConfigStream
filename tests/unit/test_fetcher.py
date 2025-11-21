import pytest
from unittest.mock import patch
from configstream.fetcher import fetch_multiple_sources, FetchResult
from configstream.adaptive_timeout import AdaptiveTimeout
from pathlib import Path

@pytest.mark.asyncio
async def test_adaptive_timeout_logic_sync():
    at = AdaptiveTimeout(
        initial=10.0, min_t=3.0, max_t=30.0, history_file=Path("dummy")
    )
    assert at.get_timeout("http://example.com") == 10.0
    for _ in range(100):
        at.record("http://example.com", 0.05)
    current = at.get_timeout("http://example.com")
    assert current < 9.0
    for _ in range(50):
        at.record("http://example.com", 15000.0)
    new_current = at.get_timeout("http://example.com")
    assert new_current > current

@pytest.mark.asyncio
async def test_fetch_multiple_batch_sync():
    with patch("configstream.fetcher.fetch_from_source") as mock_fetch:
        async def side_effect(*args, **kwargs):
            source = args[1]
            if source == "s1":
                return FetchResult(True, "s1", "data1", status_code=200, response_time=1.0)
            else:
                return FetchResult(False, "s2", error="Error", status_code=500, response_time=0.5)
        mock_fetch.side_effect = side_effect
        sources = ["s1", "s2"]
        results = await fetch_multiple_sources(sources, max_concurrent=2, timeout=5)
        assert len(results) == 2
        assert results["s1"].success
        assert not results["s2"].success
