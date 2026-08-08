# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from configstream.pipeline_stats import PipelineResult


@pytest.fixture(autouse=True)
def _disable_vwarp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_VWARP_TUNNEL", "false")


@pytest.mark.asyncio
async def test_run_full_pipeline_dry_run(tmp_path):

    # Import here to avoid stale module reference if other tests reload modules
    from configstream.pipeline import run_full_pipeline

    with (
        patch(
            "configstream.pipeline.producer.source_producer", new_callable=AsyncMock
        ) as mock_prod,
        patch(
            "configstream.pipeline.consumer.processing_consumer", new_callable=AsyncMock
        ) as mock_cons,
        patch(
            "configstream.output_handler.generate_pipeline_outputs",
            new_callable=AsyncMock,
        ) as mock_gen,
        patch(
            "configstream.pipeline.core.DEFAULT_BLOCKLIST.update",
            new_callable=AsyncMock,
        ),
        patch("configstream.pipeline.core.SingBoxTester") as mock_tester_cls,
        patch("configstream.pipeline.GeoIPResolver"),
        patch("configstream.pipeline.core.EventStream") as mock_event_stream,
    ):
        mock_tester = mock_tester_cls.return_value
        mock_tester.go_tester = MagicMock()
        mock_tester.go_tester.available = False
        mock_tester.close = AsyncMock()

        mock_event_stream.return_value.aclose = AsyncMock()
        mock_event_stream.return_value.output_dir = tmp_path / "output"

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
        patch("configstream.pipeline.producer.source_producer", new_callable=AsyncMock),
        patch(
            "configstream.pipeline.consumer.processing_consumer", new_callable=AsyncMock
        ),
        patch(
            "configstream.output_handler.generate_pipeline_outputs",
            new_callable=AsyncMock,
        ),
        patch(
            "configstream.pipeline.core.DEFAULT_BLOCKLIST.update",
            new_callable=AsyncMock,
        ),
        patch("configstream.pipeline.core.SingBoxTester") as mock_tester_cls,
        patch("configstream.pipeline.GeoIPResolver"),
        patch("multiprocessing.cpu_count", return_value=8),
        patch("configstream.pipeline.core.EventStream") as mock_event_stream,
    ):
        mock_tester = mock_tester_cls.return_value
        mock_tester.go_tester = MagicMock()
        mock_tester.go_tester.available = False
        mock_tester.close = AsyncMock()
        mock_event_stream.return_value.aclose = AsyncMock()
        mock_event_stream.return_value.output_dir = tmp_path / "output"

        await run_full_pipeline(
            ["s1"], str(tmp_path / "out"), max_workers=0, dry_run=True
        )


@pytest.mark.asyncio
async def test_pipeline_time_limit_zero_working(tmp_path):
    import asyncio
    from configstream.pipeline import run_full_pipeline

    with (
        patch("configstream.pipeline.producer.source_producer", new_callable=AsyncMock),
        patch(
            "configstream.pipeline.consumer.processing_consumer", new_callable=AsyncMock
        ),
        patch(
            "configstream.output_handler.generate_pipeline_outputs",
            new_callable=AsyncMock,
        ) as mock_gen,
        patch(
            "configstream.pipeline.core.DEFAULT_BLOCKLIST.update",
            new_callable=AsyncMock,
        ),
        patch("configstream.pipeline.core.SingBoxTester") as mock_tester_cls,
        patch("configstream.pipeline.GeoIPResolver"),
        patch("configstream.pipeline.core.EventStream") as mock_event_stream,
        patch(
            "configstream.pipeline.core.safe_wait_for", side_effect=asyncio.TimeoutError
        ),
    ):
        mock_tester = mock_tester_cls.return_value
        mock_tester.go_tester = MagicMock()
        mock_tester.go_tester.available = False
        mock_tester.close = AsyncMock()
        mock_event_stream.return_value.aclose = AsyncMock()
        mock_event_stream.return_value.output_dir = tmp_path / "output"

        res = await run_full_pipeline(
            sources=["s1"],
            output_dir=str(tmp_path / "out"),
            max_workers=5,
            time_limit_seconds=1,
            dry_run=True,
        )

        assert res.success
        assert res.stats.time_limited
        assert res.stats.working == 0
        assert mock_gen.called


@pytest.mark.asyncio
async def test_vwarp_tunnel_stopped_on_the_instance_that_started_it(
    tmp_path, monkeypatch
):
    """Shutdown must stop the VwarpTool that actually spawned the tunnel.

    The previous code called ``VwarpTool().stop_tunnel()`` on a brand-new
    instance whose ``VwarpTunnel._proc`` is None, so ``stop()`` returned
    immediately and the real child process (and its SOCKS5 port) leaked on
    every run. Distinct mock instances per construction are essential here:
    a shared MagicMock return_value would make the buggy version pass too.
    """
    from configstream.pipeline import run_full_pipeline

    monkeypatch.setenv("USE_VWARP_TUNNEL", "true")
    instances = []

    def _make_tool(*args, **kwargs):
        tool = MagicMock()
        tool.is_available = AsyncMock(return_value=True)
        tool.start_tunnel = AsyncMock(return_value=True)
        tool.stop_tunnel = AsyncMock(return_value=None)
        instances.append(tool)
        return tool

    with (
        patch("configstream.pipeline.producer.source_producer", new_callable=AsyncMock),
        patch(
            "configstream.pipeline.consumer.processing_consumer", new_callable=AsyncMock
        ),
        patch(
            "configstream.output_handler.generate_pipeline_outputs",
            new_callable=AsyncMock,
        ),
        patch(
            "configstream.pipeline.core.DEFAULT_BLOCKLIST.update",
            new_callable=AsyncMock,
        ),
        patch("configstream.pipeline.core.SingBoxTester") as mock_tester_cls,
        patch("configstream.pipeline.GeoIPResolver"),
        patch("configstream.pipeline.core.EventStream") as mock_event_stream,
        patch("configstream.tools.vwarp.manager.VwarpTool", side_effect=_make_tool),
    ):
        mock_tester = mock_tester_cls.return_value
        mock_tester.go_tester = MagicMock()
        mock_tester.go_tester.available = False
        mock_tester.close = AsyncMock()
        mock_event_stream.return_value.aclose = AsyncMock()
        mock_event_stream.return_value.output_dir = tmp_path / "output"

        await run_full_pipeline(
            sources=["http://test"],
            output_dir=str(tmp_path / "output"),
            max_workers=2,
            dry_run=True,
        )

    assert instances, "VwarpTool was never constructed"
    starter = instances[0]
    assert starter.start_tunnel.await_count == 1, "tunnel was not started"
    # The instance that started the tunnel is the one that must be stopped.
    assert (
        starter.stop_tunnel.await_count == 1
    ), "stop_tunnel was not called on the VwarpTool that started the tunnel"
