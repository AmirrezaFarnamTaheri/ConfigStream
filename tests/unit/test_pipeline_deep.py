import pytest
import asyncio
from unittest.mock import MagicMock, patch
from configstream.pipeline_stages import processing_consumer, PipelineStats
from configstream.models import Proxy
from configstream.test_cache import TestResultCache
from configstream.scheduler import SmartRetestScheduler
from configstream.concurrency_manager import ConcurrencyManager
from configstream.performance import PerformanceTracker
from configstream.source_quality import SourceQualityTracker


@pytest.mark.asyncio
async def test_processing_consumer_flow():
    queue = asyncio.Queue()
    # Put one valid item
    await queue.put(("source1", ["vmess://test"]))
    await queue.put(None)  # Stop signal

    stats = PipelineStats()
    seen_keys = set()
    final_proxies = []

    # Mocks
    mock_tester = MagicMock()
    mock_tester.go_tester.available = False  # Use Python path
    mock_tester.test = MagicMock()

    # Mock result for test() must be awaitable
    async def mock_test_result(p):
        p.is_working = True
        p.latency = 100
        return p

    mock_tester.test.side_effect = mock_test_result

    mock_scheduler = MagicMock(spec=SmartRetestScheduler)
    mock_scheduler.should_retest.return_value = True

    mock_cache = MagicMock(spec=TestResultCache)
    mock_cache.get.return_value = None

    mock_concurrency = MagicMock(spec=ConcurrencyManager)
    # mock get_semaphore must return an async context manager
    # asyncio.Semaphore is one.
    mock_concurrency.get_semaphore.return_value = asyncio.Semaphore(10)
    mock_concurrency.record = MagicMock()  # awaitable? record is async def

    async def mock_record(*args):
        pass

    # We also need start_tuner and stop_tuner
    mock_concurrency.start_tuner = MagicMock()
    # Ensure stop_tuner is awaitable
    f = asyncio.Future()
    f.set_result(None)
    mock_concurrency.stop_tuner = MagicMock(return_value=f)

    mock_concurrency.record.side_effect = mock_record

    mock_geoip = MagicMock()
    mock_geoip.lookup.return_value = MagicMock(
        country_code="US", city="Test", asn="AS1", org="Org"
    )

    tracker = PerformanceTracker()
    mock_quality = MagicMock(spec=SourceQualityTracker)

    # Need to mock parse_config or ensure "vmess://test" parses
    with patch("configstream.pipeline_core.consumer.parse_config") as mock_parse:
        # Return a valid proxy
        p = Proxy(config="vmess://test", protocol="vmess", address="1.1.1.1", port=443)
        mock_parse.return_value = p

        # We also need to mock validate_batch_configs to just return the list
        with patch(
            "configstream.pipeline_core.consumer.validate_batch_configs"
        ) as mock_validate:
            mock_validate.side_effect = lambda batch, policy: batch

            await processing_consumer(
                work_queue=queue,
                stats=stats,
                seen_keys=seen_keys,
                final_proxies=final_proxies,
                tester=mock_tester,
                scheduler=mock_scheduler,
                test_cache=mock_cache,
                concurrency=mock_concurrency,
                geoip=mock_geoip,
                tracker=tracker,
                event_stream=None,
                quality_tracker=mock_quality,
                progress=None,
                task_process=None,
                max_proxies=None,
                max_latency=None,
                country_filter=None,
                leniency=False,
            )

    assert len(final_proxies) == 1
    assert final_proxies[0].country_code == "US"
    assert stats.working == 1
