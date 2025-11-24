import pytest
from unittest.mock import MagicMock, patch
from configstream.pipeline import run_full_pipeline
from configstream.models import Proxy
from configstream.intelligence.washer import ProxyWasher


@pytest.fixture
def mock_proxies():
    p1 = Proxy(
        config="vless://1",
        protocol="vless",
        address="1.1.1.1",
        port=443,
        uuid="u1",
        is_working=True,
        latency=100,
        country_code="US",
        city="New York",
        asn="AS123",
        org="ISP1",
        country="United States",
    )

    p2 = Proxy(
        config="vmess://2",
        protocol="vmess",
        address="2.2.2.2",
        port=443,
        uuid="u2",
        is_working=True,
        latency=200,
        country_code="DE",
        city="Berlin",
        asn="AS456",
        org="ISP2",
        country="Germany",
    )

    return [p1, p2]


@pytest.mark.asyncio
async def test_pipeline_dry_run(tmp_path, mock_proxies):
    with (
        patch("configstream.pipeline.SingBoxTester"),
        patch("configstream.pipeline.SourceQualityTracker"),
        patch("configstream.pipeline.AnomalyDetector"),
        patch("configstream.pipeline.EventStream"),
        patch("configstream.pipeline.source_producer") as mock_producer,
        patch("configstream.pipeline.processing_consumer") as mock_consumer,
        patch(
            "configstream.pipeline.filter_unique_endpoints", return_value=mock_proxies
        ),
        patch(
            "configstream.pipeline_core.output_handler.generate_categorized_outputs", return_value={}
        ),
        patch("configstream.pipeline_core.output_handler.save_metadata"),
        patch("configstream.pipeline_core.output_handler.generate_vectors"),
        patch("configstream.pipeline.ProxyHistoryTracker") as MockHistory,
        patch(
            "configstream.pipeline_core.output_handler.ProxyWasher", new=MagicMock(spec=ProxyWasher)
        ) as MockWasher,
        patch("configstream.pipeline_core.output_handler.get_adapter"),
        patch("configstream.pipeline_core.output_handler.select_top_configs", return_value=mock_proxies),
        patch("configstream.pipeline_core.output_handler.generate_smart_chains", return_value={}),
    ):

        history = MagicMock()
        history.get_reliability_score.return_value = 0.9
        history.get_summary_stats.return_value = {"uptime_percentage": 90}
        history.get_history.return_value = []
        MockHistory.return_value = history

        MockWasher.return_value.wash_batch.return_value = ([], set())

        async def fake_producer(*args, **kwargs):
            pass

        async def fake_consumer(queue, stats, seen, final_proxies, *args, **kwargs):
            final_proxies.extend(mock_proxies)
            stats.working = len(mock_proxies)

        mock_producer.side_effect = fake_producer
        mock_consumer.side_effect = fake_consumer

        result = await run_full_pipeline(
            sources=["http://test"],
            output_dir=str(tmp_path),
            dry_run=True,
            proxies=mock_proxies,
        )

        assert result.success is True
        assert result.stats.final_count == 2
        assert (tmp_path / "chosen" / "proxies.json").exists()


@pytest.mark.asyncio
async def test_pipeline_pareto_sort(tmp_path, mock_proxies):
    with (
        patch("configstream.pipeline.SingBoxTester"),
        patch("configstream.pipeline.SourceQualityTracker"),
        patch("configstream.pipeline.AnomalyDetector"),
        patch("configstream.pipeline.EventStream"),
        patch("configstream.pipeline.source_producer"),
        patch("configstream.pipeline.processing_consumer") as mock_consumer,
        patch(
            "configstream.pipeline.filter_unique_endpoints", return_value=mock_proxies
        ),
        patch(
            "configstream.pipeline_core.output_handler.generate_categorized_outputs", return_value={}
        ),
        patch("configstream.pipeline_core.output_handler.save_metadata"),
        patch("configstream.pipeline_core.output_handler.generate_vectors"),
        patch("configstream.pipeline.ProxyHistoryTracker") as MockHistory,
        patch(
            "configstream.pipeline_core.output_handler.ProxyWasher", new=MagicMock(spec=ProxyWasher)
        ) as MockWasher,
        patch("configstream.pipeline_core.output_handler.get_adapter"),
        patch("configstream.pipeline_core.output_handler.select_top_configs", return_value=mock_proxies),
        patch("configstream.pipeline_core.output_handler.generate_smart_chains", return_value={}),
    ):

        MockWasher.return_value.wash_batch.return_value = ([], set())

        history = MagicMock()

        def get_rel(id):
            return 0.9 if id == "u1" else 0.1  # Using uuid as id

        history.get_reliability_score.side_effect = get_rel
        history.get_summary_stats.return_value = {"uptime_percentage": 90}
        history.get_history.return_value = []
        MockHistory.return_value = history

        async def fake_consumer(queue, stats, seen, final_proxies, *args, **kwargs):
            final_proxies.extend(mock_proxies)

        mock_consumer.side_effect = fake_consumer

        await run_full_pipeline(
            sources=[], output_dir=str(tmp_path), proxies=mock_proxies
        )

        from configstream.pipeline_core import output_handler

        args, _ = output_handler.generate_categorized_outputs.call_args
        sorted_proxies = args[0]

        assert sorted_proxies[0].id == "u1"
        assert sorted_proxies[1].id == "u2"


@pytest.mark.asyncio
async def test_pipeline_adapter_export_fail(tmp_path, mock_proxies):
    with (
        patch("configstream.pipeline.SingBoxTester"),
        patch("configstream.pipeline.SourceQualityTracker"),
        patch("configstream.pipeline.AnomalyDetector"),
        patch("configstream.pipeline.EventStream"),
        patch("configstream.pipeline.source_producer"),
        patch(
            "configstream.pipeline.processing_consumer",
            side_effect=lambda *args, **kwargs: args[3].extend(mock_proxies),
        ),
        patch(
            "configstream.pipeline.filter_unique_endpoints", return_value=mock_proxies
        ),
        patch(
            "configstream.pipeline_core.output_handler.generate_categorized_outputs", return_value={}
        ),
        patch("configstream.pipeline_core.output_handler.save_metadata"),
        patch("configstream.pipeline_core.output_handler.generate_vectors"),
        patch("configstream.pipeline.ProxyHistoryTracker") as MockHistory,
        patch(
            "configstream.pipeline_core.output_handler.ProxyWasher", new=MagicMock(spec=ProxyWasher)
        ) as MockWasher,
        patch("configstream.pipeline_core.output_handler.get_adapter") as mock_get_adapter,
        patch("configstream.pipeline_core.output_handler.select_top_configs", return_value=mock_proxies),
        patch("configstream.pipeline_core.output_handler.generate_smart_chains", return_value={}),
    ):

        MockWasher.return_value.wash_batch.return_value = ([], set())

        history = MagicMock()
        history.get_reliability_score.return_value = 0.5
        history.get_summary_stats.return_value = {}
        history.get_history.return_value = []
        MockHistory.return_value = history

        mock_get_adapter.side_effect = Exception("Adapter Error")

        result = await run_full_pipeline(sources=[], output_dir=str(tmp_path))

        assert result.success is True
