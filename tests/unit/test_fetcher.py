import pytest
from unittest.mock import AsyncMock, patch
from configstream.fetcher import SourceFetcher


@pytest.mark.asyncio
async def test_source_fetcher_fetch_all():
    """Test that the source fetcher correctly fetches all sources."""
    with patch(
        "configstream.fetcher.fetch_multiple_sources",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = {
            "http://source1": AsyncMock(success=True, configs=["config1", "config2"], error=None),
            "http://source2": AsyncMock(success=True, configs=["config3"], error=None),
            "http://source3": AsyncMock(success=False, configs=[], error="Fetch failed"),
        }

        fetcher = SourceFetcher()
        configs = await fetcher.fetch_all(["http://source1", "http://source2", "http://source3"])

        assert len(configs) == 3
        assert "config1" in configs
        assert "config2" in configs
        assert "config3" in configs


@pytest.mark.asyncio
async def test_source_fetcher_fetch_all_with_max_proxies():
    """Test that the source fetcher respects the max_proxies limit."""
    with patch(
        "configstream.fetcher.fetch_multiple_sources",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = {
            "http://source1": AsyncMock(
                success=True, configs=["config1", "config2", "config3"], error=None
            ),
        }

        fetcher = SourceFetcher()
        configs = await fetcher.fetch_all(["http://source1"], max_proxies=2)

        assert len(configs) == 2
        assert "config1" in configs
        assert "config2" in configs
        assert "config3" not in configs
