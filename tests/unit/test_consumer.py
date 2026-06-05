# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from configstream.pipeline.consumer import processing_consumer
from configstream.pipeline_stats import PipelineStats
from configstream.models import Proxy


@pytest.fixture
def mock_dependencies_fix():
    queue = asyncio.Queue()

    # Mocks
    tester = MagicMock()
    tester.go_tester.available = True  # Enable Go tester to trigger revival logic
    tester.test = AsyncMock()
    tester.test_batch = AsyncMock()

    washer = MagicMock()

    scheduler = MagicMock()
    scheduler.should_retest.return_value = True

    test_cache = MagicMock()
    test_cache.get.return_value = None

    concurrency = MagicMock()
    concurrency.get_semaphore.return_value = AsyncMock()
    concurrency.get_semaphore.return_value.__aenter__.return_value = None
    concurrency.get_semaphore.return_value.__aexit__.return_value = None
    concurrency.record = AsyncMock()

    geoip = MagicMock()
    geoip.lookup = AsyncMock(return_value=None)

    tracker = MagicMock()
    tracker.phase.return_value = MagicMock()
    tracker.phase.return_value.__enter__.return_value = None
    tracker.phase.return_value.__exit__.return_value = None

    history = MagicMock()
    history.update_history = MagicMock()

    quality = MagicMock()

    return {
        "queue": queue,
        "tester": tester,
        "washer": washer,
        "scheduler": scheduler,
        "test_cache": test_cache,
        "concurrency": concurrency,
        "geoip": geoip,
        "tracker": tracker,
        "history": history,
        "quality": quality,
    }


@pytest.mark.asyncio
async def test_processing_consumer_revival_crash(mock_dependencies_fix):
    deps = mock_dependencies_fix
    queue = deps["queue"]
    stats = PipelineStats()
    seen_keys = set()
    final_proxies = []

    # 1. Setup Input: A proxy that will fail initially
    await queue.put(("test-source", ["vmess://test"]))
    await queue.put(None)  # Sentinel

    original_proxy = Proxy(
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        config="vmess://test",
        uuid="orig1",
    )

    # Mock parse_config
    with patch("configstream.consumer.parse_config", return_value=original_proxy):
        # Mock validate_batch_configs
        with patch(
            "configstream.consumer.validate_batch_configs",
            return_value=[original_proxy],
        ):

            # 2. Make initial test fail
            # tester.test_batch updates in place.
            async def fail_initial_batch(batch):
                for p in batch:
                    p.is_working = False

            deps["tester"].test_batch.side_effect = fail_initial_batch

            # 3. Setup Washer to return a revived proxy
            # The revived proxy has origin_proxy as a dict
            origin_dict = original_proxy.model_dump(mode="json")
            revived_proxy = Proxy(
                protocol="revived",
                address="clean.ip",
                port=2408,
                config="revived://",
                details={"origin_proxy": origin_dict},
            )

            # washer.wash_failed returns (candidates, count)
            deps["washer"].wash_failed.return_value = ([revived_proxy], 1)

            # 4. Make revival test succeed

            async def smart_test_batch(batch):
                for p in batch:
                    if p.protocol == "revived":
                        p.is_working = True
                        p.latency = 50
                    else:
                        p.is_working = False

            deps["tester"].test_batch.side_effect = smart_test_batch

            # Run consumer - should NOT crash
            await processing_consumer(
                work_queue=queue,
                stats=stats,
                seen_keys=seen_keys,
                final_proxies=final_proxies,
                tester=deps["tester"],
                scheduler=deps["scheduler"],
                test_cache=deps["test_cache"],
                concurrency=deps["concurrency"],
                geoip=deps["geoip"],
                tracker=deps["tracker"],
                event_stream=None,
                quality_tracker=deps["quality"],
                history=deps["history"],
                progress=None,
                task_process=None,
                max_latency=None,
                country_filter=None,
                leniency=False,
                washer=deps["washer"],
            )

    # Assert correctness
    # Vwarp success skips the fallback Warp retry for the same proxy.
    assert len(final_proxies) == 1
    assert final_proxies[0].protocol == "revived"
