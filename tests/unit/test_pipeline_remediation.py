# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for pipeline consumer fallback cache bypass and infra_failure handling."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from configstream.models import Proxy
from configstream.test_cache import TestResultCache
from configstream.pipeline.consumer import _test_candidates
from configstream.concurrency_manager import ConcurrencyManager
from configstream.pipeline_stats import PipelineStats
from configstream.config import AppSettings


def _make_proxy(address: str = "1.1.1.1", port: int = 443) -> Proxy:
    return Proxy(
        config=f"vless://00000000-0000-0000-0000-000000000001@{address}:{port}",
        protocol="vless",
        address=address,
        port=port,
        uuid="00000000-0000-0000-0000-000000000001",
    )


@pytest.mark.asyncio
async def test_fallback_test_invalidates_cache_and_invokes_python_tester(tmp_path):
    """When Go tester marks proxy with infra_failure=True, consumer must invalidate cache and run python_tester."""
    db_file = tmp_path / "test_cache.json"
    cache = TestResultCache(db_path=str(db_file), ttl_seconds=3600)

    p = _make_proxy("10.0.0.1", 443)

    # Store a stale failure entry in cache
    p_cached = _make_proxy("10.0.0.1", 443)
    p_cached.is_working = False
    p_cached.details["error"] = "GO_IPC_TIMEOUT"
    cache.set(p_cached)

    # Verify entry exists in cache
    assert cache.contains(p) is True

    # Mock tester hierarchy
    tester = MagicMock()
    tester.go_tester = MagicMock()
    tester.go_tester.available = True

    async def fake_go_batch(chunk):
        for item in chunk:
            item.is_working = False
            item.details["infra_failure"] = True
            item.details["error"] = "BATCH_TIMEOUT"

    tester.test_batch = AsyncMock(side_effect=fake_go_batch)

    # Mock python_tester.test_via_singbox returning working proxy
    async def fake_python_test(item):
        py_proxy = _make_proxy(item.address, item.port)
        py_proxy.is_working = True
        py_proxy.latency = 45.0
        return py_proxy

    tester.python_tester = MagicMock()
    tester.python_tester.test_via_singbox = AsyncMock(side_effect=fake_python_test)

    scheduler = MagicMock()
    scheduler.should_retest.return_value = True

    loop = asyncio.get_running_loop()
    concurrency = ConcurrencyManager(loop=loop)
    history = MagicMock()
    stats = PipelineStats()
    seen_lock = asyncio.Lock()

    final_working, failed, tested_count = await _test_candidates(
        safe_batch=[p],
        tester=tester,
        scheduler=scheduler,
        test_cache=cache,
        concurrency=concurrency,
        history=history,
        stats=stats,
        seen_lock=seen_lock,
        loop=loop,
        progress=None,
        task_process=None,
        settings=AppSettings(),
    )

    # Verify python_tester.test_via_singbox was invoked directly
    tester.python_tester.test_via_singbox.assert_called_once_with(p)

    # Verify proxy was restored to working status via python fallback
    assert len(final_working) == 1
    assert final_working[0].is_working is True
    assert final_working[0].latency == 45.0
