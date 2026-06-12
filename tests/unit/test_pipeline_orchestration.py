# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from configstream.pipeline_stats import PipelineResult


@pytest.mark.asyncio
async def test_run_full_pipeline_dry_run(tmp_path):
    # Import here to avoid stale module reference if other tests reload modules
    from configstream.pipeline import run_full_pipeline

    with (
        patch(
            "configstream.pipeline.source_producer", new_callable=AsyncMock
        ) as mock_prod,
        patch(
            "configstream.pipeline.processing_consumer", new_callable=AsyncMock
        ) as mock_cons,
        patch(
            "configstream.output_handler.generate_pipeline_outputs",
            new_callable=AsyncMock,
        ) as mock_gen,
        patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new_callable=AsyncMock),
        patch("configstream.pipeline.SingBoxTester") as mock_tester_cls,
        patch("configstream.pipeline.GeoIPResolver"),
        patch("configstream.pipeline.EventStream") as mock_event_stream,
    ):

        mock_tester = mock_tester_cls.return_value
        mock_tester.go_tester = MagicMock()
        mock_tester.go_tester.available = False
        mock_tester.close = AsyncMock()

        mock_event_stream.return_value.aclose = AsyncMock()

        output_dir = tmp_path / "output"

        res = await run_full_pipeline(
            sources=["http://test"],
            output_dir=str(output_dir),
            max_workers=5,
            dry_run=True,
        )

        assert isinstance(res, PipelineResult)
        assert res.success
        assert mock_prod.called, "source_producer should have been called"
        assert mock_cons.called, "processing_consumer should have been called"
        assert mock_gen.called, "generate_pipeline_outputs should have been called"


@pytest.mark.asyncio
async def test_pipeline_auto_scaling(tmp_path):
    # Import here to avoid stale module reference if other tests reload modules
    from configstream.pipeline import run_full_pipeline

    with (
        patch("configstream.pipeline.source_producer", new_callable=AsyncMock),
        patch("configstream.pipeline.processing_consumer", new_callable=AsyncMock),
        patch(
            "configstream.output_handler.generate_pipeline_outputs",
            new_callable=AsyncMock,
        ),
        patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new_callable=AsyncMock),
        patch("configstream.pipeline.SingBoxTester") as mock_tester_cls,
        patch("configstream.pipeline.GeoIPResolver"),
        patch("multiprocessing.cpu_count", return_value=8),
        patch("configstream.pipeline.EventStream") as mock_event_stream,
    ):

        mock_tester = mock_tester_cls.return_value
        mock_tester.go_tester = MagicMock()
        mock_tester.go_tester.available = False
        mock_tester.close = AsyncMock()
        mock_event_stream.return_value.aclose = AsyncMock()

        await run_full_pipeline(["s1"], str(tmp_path / "out"), max_workers=0)


@pytest.mark.asyncio
async def test_pipeline_time_limit_zero_working(tmp_path):
    import asyncio
    from configstream.pipeline import run_full_pipeline

    with (
        patch("configstream.pipeline.source_producer", new_callable=AsyncMock),
        patch("configstream.pipeline.processing_consumer", new_callable=AsyncMock),
        patch(
            "configstream.output_handler.generate_pipeline_outputs",
            new_callable=AsyncMock,
        ) as mock_gen,
        patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new_callable=AsyncMock),
        patch("configstream.pipeline.SingBoxTester") as mock_tester_cls,
        patch("configstream.pipeline.GeoIPResolver"),
        patch("configstream.pipeline.EventStream") as mock_event_stream,
        patch("configstream.pipeline.core.safe_wait_for", side_effect=asyncio.TimeoutError),
    ):
        mock_tester = mock_tester_cls.return_value
        mock_tester.go_tester = MagicMock()
        mock_tester.go_tester.available = False
        mock_tester.close = AsyncMock()
        mock_event_stream.return_value.aclose = AsyncMock()

        res = await run_full_pipeline(
            sources=["s1"],
            output_dir=str(tmp_path / "out"),
            max_workers=5,
            time_limit_seconds=1,
        )

        assert res.success
        assert res.stats.time_limited
        assert res.stats.working == 0
        assert mock_gen.called
