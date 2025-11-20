
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import pytest

from configstream.fetcher import fetch_multiple_sources, FetchResult
from configstream.adaptive_timeout import AdaptiveTimeout


@pytest.mark.asyncio
async def test_adaptive_timeout_logic_sync():
    # Use a dummy file to avoid loading from real history
    at = AdaptiveTimeout(
        initial=10.0, min_t=3.0, max_t=30.0, history_file=Path("dummy")
    )
    assert at.get_timeout("http://example.com") == 10.0

    # More iterations to ensure moving average moves enough
    for _ in range(100):
        at.record("http://example.com", 0.05)  # 50ms = 0.05s

    current = at.get_timeout("http://example.com")
    # Target = 0.05 * 2 = 0.1s. Initial 10.0.
    # With alpha=0.1, after 100 iterations of ~0.1s target,
    # the timeout should drift down from 10.0s towards 0.1s.
    # It should definitely be less than 9.0s.
    assert current < 9.0

    for _ in range(50):
        at.record("http://example.com", 15000.0)  # 15s

    new_current = at.get_timeout("http://example.com")
    # Should have increased
    assert new_current > current


@pytest.mark.asyncio
async def test_fetch_multiple_batch_sync():
    with patch("configstream.fetcher.fetch_from_source") as mock_fetch:

        async def side_effect(*args, **kwargs):
            source = args[1]
            if source == "s1":
                return FetchResult(
                    source="s1",
                    content="data1",
                    success=True,
                    status_code=200,
                    response_time=1.0,
                    error=None,
                )
            else:
                return FetchResult(
                    source="s2",
                    content=None,
                    success=False,
                    status_code=500,
                    response_time=0.5,
                    error="Error",
                )

        mock_fetch.side_effect = side_effect

        sources = ["s1", "s2"]
        results = await fetch_multiple_sources(
            sources, max_concurrent=2, timeout=5
        )

        assert len(results) == 2
        assert results["s1"].success
        assert not results["s2"].success
