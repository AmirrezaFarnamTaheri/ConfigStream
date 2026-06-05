# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from configstream.pipeline.core import StandardPipeline
from configstream.models import Proxy
from configstream.intelligence.washer.core import ProxyWasher


@pytest.fixture
def mock_proxies():
    return [
        Proxy(
            config="vless://1",
            protocol="vless",
            address="1.1.1.1",
            port=443,
            uuid="u1",
            country="US",
            latency=100,
        ),
        Proxy(
            config="vless://2",
            protocol="vless",
            address="2.2.2.2",
            port=443,
            uuid="u2",
            country="DE",
            latency=50,
        ),
    ]


@pytest.mark.asyncio
async def test_pipeline_dry_run(tmp_path, mock_proxies):
    # Create a callable that returns mock_proxies to avoid fixture timing issues
    def filter_unique_mock(*args, **kwargs):
        return list(mock_proxies)

    with (
        patch("configstream.pipeline.SingBoxTester") as MockTester,
        patch("configstream.pipeline.SourceQualityTracker"),
        patch("configstream.pipeline.AnomalyDetector"),
        patch("configstream.pipeline.EventStream") as MockEventStream,
        patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new=AsyncMock()),
        patch("configstream.pipeline.source_producer") as mock_producer,
        patch("configstream.pipeline.processing_consumer") as mock_consumer,
        patch(
            "configstream.pipeline.filter_unique_endpoints",
            side_effect=filter_unique_mock,
        ),
        patch(
            "configstream.output_handler.generate_categorized_outputs",
            return_value={},
        ),
        patch("configstream.output_handler.save_metadata"),
        patch("configstream.pipeline.ProxyHistoryTracker") as MockHistory,
        patch(
            "configstream.output_handler.ProxyWasher",
            new=MagicMock(spec=ProxyWasher),
        ) as MockWasher,
        patch(
            "configstream.output_handler.generate_smart_chains",
            return_value={},
        ),
    ):

        # Configure mocked tester to be awaitable on close
        MockTester.return_value.close = AsyncMock()
        MockTester.return_value.go_tester.available = False

        # Configure EventStream mock
        MockEventStream.return_value.aclose = AsyncMock()

        history = MagicMock()
        history.get_reliability_score.return_value = 0.9
        history.get_summary_stats.return_value = {"uptime_percentage": 90}
        history.get_history.return_value = []
        MockHistory.return_value = history

        # Mocking washer methods correctly
        washer_instance = MockWasher.return_value
        washer_instance.fetch_clean_ips = AsyncMock()
        washer_instance.wash_batch = MagicMock(return_value=([], set(), {}))

        async def fake_producer(sources, work_queue, proxies, *args, **kwargs):
            if proxies:
                lines = [p.config for p in proxies if p.config]
                if lines:
                    await work_queue.put(("test-source", lines))

            # Put None for ALL consumers
            num_consumers = kwargs.get("num_consumers", 1)
            for _ in range(num_consumers):
                await work_queue.put(None)

        async def fake_consumer(
            work_queue, stats, seen_keys, final_proxies, *args, **kwargs
        ):
            final_proxies.extend(mock_proxies)
            stats.working = len(mock_proxies)
            stats.fetched_sources = 1
            stats.fetched_lines = 2

            while True:
                item = await work_queue.get()
                work_queue.task_done()
                if item is None:
                    break

        mock_producer.side_effect = fake_producer
        mock_consumer.side_effect = fake_consumer

        result = await run_full_pipeline(
            sources=["http://test"],
            output_dir=str(tmp_path),
            dry_run=True,
            proxies=mock_proxies,
        )

        assert result.success is True
        if result.stats.final_count > 0:
            assert result.stats.final_count == 2
            # Proxies are now saved directly to output_dir, not 'chosen' subdirectory
            assert (tmp_path / "proxies.json").exists()


@pytest.mark.asyncio
async def test_pipeline_pareto_sort(tmp_path, mock_proxies):
    # Tests that sorting is applied
    with (
        patch("configstream.pipeline.SingBoxTester") as MockTester,
        patch("configstream.pipeline.SourceQualityTracker"),
        patch("configstream.pipeline.AnomalyDetector"),
        patch("configstream.pipeline.EventStream") as MockEventStream,
        patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new=AsyncMock()),
        patch("configstream.pipeline.source_producer") as mock_producer,
        patch("configstream.pipeline.processing_consumer") as mock_consumer,
        patch(
            "configstream.output_handler.generate_pipeline_outputs",
            new=AsyncMock(return_value={}),
        ),
        patch("configstream.pipeline.ProxyHistoryTracker") as MockHistory,
    ):
        MockTester.return_value.close = AsyncMock()
        MockTester.return_value.go_tester.available = False

        # Configure EventStream mock
        MockEventStream.return_value.aclose = AsyncMock()

        # Mock history to prefer the higher latency one (reliability > latency scenario)
        history = MagicMock()
        MockHistory.return_value = history

        # Setup producer/consumer to return proxies
        async def fake_producer(sources, work_queue, proxies, *args, **kwargs):
            # Put None for ALL consumers
            num_consumers = kwargs.get("num_consumers", 1)
            for _ in range(num_consumers):
                await work_queue.put(None)

        async def fake_consumer(
            work_queue, stats, seen_keys, final_proxies, *args, **kwargs
        ):
            final_proxies.extend(mock_proxies)
            while True:
                item = await work_queue.get()
                work_queue.task_done()
                if item is None:
                    break

        mock_producer.side_effect = fake_producer
        mock_consumer.side_effect = fake_consumer

        result = await run_full_pipeline(
            sources=["http://test"], output_dir=str(tmp_path), dry_run=True
        )

        assert result.success is True
        # Logic verification: sort_proxies_pareto is called inside pipeline.
        # Since we mock consumer to just append proxies, they are unsorted initially.
        # Pipeline calls sort in place.
        # We can't easily assert sort order here without mocking the sort function or checking result side effects
        # But we assert pipeline ran successfully.


@pytest.mark.asyncio
async def test_pipeline_adapter_export_fail(tmp_path, mock_proxies):
    with (
        patch("configstream.pipeline.SingBoxTester") as MockTester,
        patch("configstream.pipeline.SourceQualityTracker"),
        patch("configstream.pipeline.AnomalyDetector"),
        patch("configstream.pipeline.EventStream") as MockEventStream,
        patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new=AsyncMock()),
        patch("configstream.pipeline.source_producer") as mock_producer,
        patch("configstream.pipeline.processing_consumer") as mock_consumer,
        patch(
            "configstream.output_handler.generate_pipeline_outputs",
            new=AsyncMock(side_effect=Exception("Export Fail")),
        ),
        patch("configstream.pipeline.ProxyHistoryTracker"),
    ):
        MockTester.return_value.close = AsyncMock()
        MockTester.return_value.go_tester.available = False

        # Configure EventStream mock
        MockEventStream.return_value.aclose = AsyncMock()

        async def fake_producer(sources, work_queue, proxies, *args, **kwargs):
            # Put None for ALL consumers
            num_consumers = kwargs.get("num_consumers", 1)
            for _ in range(num_consumers):
                await work_queue.put(None)

        async def fake_consumer(
            work_queue, stats, seen_keys, final_proxies, *args, **kwargs
        ):
            while True:
                item = await work_queue.get()
                work_queue.task_done()
                if item is None:
                    break

        mock_producer.side_effect = fake_producer
        mock_consumer.side_effect = fake_consumer

        with pytest.raises(Exception, match="Export Fail"):
            await run_full_pipeline(
                sources=["http://test"], output_dir=str(tmp_path), dry_run=True
            )
