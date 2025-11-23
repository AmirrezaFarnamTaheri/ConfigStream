import pytest
import asyncio
from unittest.mock import MagicMock, patch
from configstream.pipeline_stages import source_producer
from configstream.models import Proxy


@pytest.mark.asyncio
async def test_source_producer():
    queue = asyncio.Queue()
    sources = ["http://example.com/source1"]

    # Mock dependencies
    mock_quality = MagicMock()
    mock_quality.should_fetch.return_value = True

    mock_anomaly = MagicMock()
    # Allow everything
    mock_anomaly.is_safe.return_value = (True, "Safe")

    # Mock fetcher - CRITICAL step
    with patch("configstream.pipeline_stages.fetch_multiple_sources") as mock_fetch:
        # Create a mock result
        mock_res = MagicMock()
        mock_res.success = True
        mock_res.content = "vmess://test"
        mock_fetch.return_value = {"http://example.com/source1": mock_res}

        await source_producer(
            sources, queue, None, mock_quality, mock_anomaly, None, None, None
        )

    # Check queue has the lines
    item = await queue.get()
    # Item structure is (source, lines)
    assert item[0] == "http://example.com/source1"
    assert "vmess://test" in item[1]

    # Check shutdown signal
    signal = await queue.get()
    assert signal is None
