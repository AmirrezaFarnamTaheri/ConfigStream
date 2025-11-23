import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from configstream.pipeline_stages import processing_consumer, PipelineStats
from configstream.models import Proxy
from configstream.testers_core import SingBoxTester


@pytest.fixture
def mock_work_queue():
    queue = asyncio.Queue()
    return queue


@pytest.fixture
def mock_tester():
    tester = MagicMock(spec=SingBoxTester)
    tester.go_tester = MagicMock()
    tester.go_tester.available = False
    tester.test = AsyncMock(
        return_value=Proxy(
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            is_working=True,
            latency=100,
            config="vmess://test",
        )
    )
    return tester


@pytest.fixture
def mock_quality_tracker():
    tracker = MagicMock()
    tracker.should_fetch = MagicMock(return_value=True)
    return tracker


@pytest.fixture
def mock_concurrency():
    cm = MagicMock()
    cm.get_semaphore = MagicMock(return_value=AsyncMock())
    cm.get_semaphore.return_value.__aenter__ = AsyncMock()
    cm.get_semaphore.return_value.__aexit__ = AsyncMock()
    cm.start_tuner = MagicMock()
    cm.stop_tuner = AsyncMock()
    cm.record = AsyncMock()
    return cm


@pytest.mark.asyncio
async def test_processing_consumer_basic(
    mock_work_queue, mock_tester, mock_quality_tracker, mock_concurrency
):
    stats = PipelineStats()
    seen_keys = set()
    final_proxies = []

    # Mock dependencies
    scheduler = MagicMock()
    scheduler.should_retest = MagicMock(return_value=True)

    test_cache = MagicMock()
    test_cache.get = MagicMock(return_value=None)

    geoip = MagicMock()
    geoip.lookup = MagicMock(
        return_value=MagicMock(
            country_code="US", city="Test City", asn="AS1234", org="Test Org"
        )
    )

    tracker = MagicMock()
    tracker.phase = MagicMock(
        return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
    )

    # Add item to queue
    raw_lines = ["vmess://eyJaddfqwefqwe..."]  # Mock line
    source = "test_source"
    await mock_work_queue.put((source, raw_lines))
    await mock_work_queue.put(None)  # Signal end

    # Mock parse_config to return a proxy
    with patch(
        "configstream.pipeline_stages.parse_config",
        return_value=Proxy(
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            config="vmess://...",
            details={},
        ),
    ):
        with patch(
            "configstream.pipeline_stages.validate_batch_configs",
            return_value=[
                Proxy(
                    protocol="vmess",
                    address="1.1.1.1",
                    port=443,
                    config="vmess://...",
                    details={},
                )
            ],
        ):
            await processing_consumer(
                mock_work_queue,
                stats,
                seen_keys,
                final_proxies,
                mock_tester,
                scheduler,
                test_cache,
                mock_concurrency,
                geoip,
                tracker,
                None,  # event_stream
                mock_quality_tracker,
                None,  # progress
                None,  # task_process
                max_proxies=None,
                max_latency=None,
                country_filter=None,
                leniency=False,
            )

    assert stats.fetched_sources == 1
    assert stats.fetched_lines == 1
    assert stats.parsed == 1
    assert len(final_proxies) == 1
    assert final_proxies[0].country_code == "US"
