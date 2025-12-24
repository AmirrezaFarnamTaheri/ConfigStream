import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import configstream.pipeline
from configstream.pipeline import run_full_pipeline
from configstream.pipeline_core.models import PipelineResult


@pytest.mark.asyncio
async def test_run_full_pipeline_dry_run(tmp_path):
    # Use string-based patches to ensure we hit the right namespace
    with (
        patch("configstream.pipeline.source_producer", new_callable=AsyncMock) as mock_prod,
        patch("configstream.pipeline.processing_consumer", new_callable=AsyncMock) as mock_cons,
        patch(
            "configstream.pipeline.output_handler.generate_pipeline_outputs",
            new_callable=AsyncMock,
        ) as mock_gen,
        patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new_callable=AsyncMock),
        patch("configstream.pipeline.SingBoxTester") as mock_tester_cls,
        patch("configstream.pipeline.GeoIPResolver"),
        patch("configstream.pipeline.EventStream") as mock_event_stream,
        # Also patch pipeline_stages just in case
        patch("configstream.pipeline_stages.source_producer", new=AsyncMock()),
        patch("configstream.pipeline_stages.processing_consumer", new=AsyncMock()),
    ):

        mock_tester = mock_tester_cls.return_value
        mock_tester.go_tester = MagicMock()
        mock_tester.go_tester.available = False
        mock_tester.close = AsyncMock()

        # Mock event stream aclose
        mock_event_stream.return_value.aclose = AsyncMock()

        output_dir = tmp_path / "output"

        # Call the function
        res = await run_full_pipeline(
            sources=["http://test"],
            output_dir=str(output_dir),
            max_workers=5,
            dry_run=True,
        )

        assert isinstance(res, PipelineResult)
        assert res.success

        # Verify mocks were called
        assert mock_prod.called, "source_producer should have been called"
        assert mock_cons.called, "processing_consumer should have been called"
        assert mock_gen.called, "generate_pipeline_outputs should have been called"


@pytest.mark.asyncio
async def test_pipeline_auto_scaling(tmp_path):
    with (
        patch("configstream.pipeline.source_producer", new_callable=AsyncMock),
        patch("configstream.pipeline.processing_consumer", new_callable=AsyncMock),
        patch(
            "configstream.pipeline.output_handler.generate_pipeline_outputs",
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
