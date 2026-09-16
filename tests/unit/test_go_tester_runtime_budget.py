# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.testers.go_tester.manager import GoBatchTester


def test_go_tester_timeout_threshold_is_configurable(monkeypatch) -> None:
    monkeypatch.setenv("GO_TESTER_MAX_CONSECUTIVE_TIMEOUTS", "3")

    tester = GoBatchTester(binary_path="/definitely-not-present")

    assert tester._max_consecutive_timeouts == 3


def test_go_tester_result_timeout_scales_with_worker_waves() -> None:
    fast = GoBatchTester(binary_path="/definitely-not-present", workers=128, timeout=15)
    conservative = GoBatchTester(
        binary_path="/definitely-not-present", workers=20, timeout=10
    )

    assert fast._result_timeout_seconds(500) == 90.0
    assert conservative._result_timeout_seconds(500) == 280.0
    assert fast._result_timeout_seconds(1) == 60.0
    assert fast._result_timeout_seconds(0) == 60.0


def _make_custom_tester() -> Any:
    tester: Any = object.__new__(GoBatchTester)
    tester.workers = 20
    tester.timeout = 10
    tester.binary_path = "dummy"
    tester.available = True
    tester._proc = MagicMock()
    tester._proc.returncode = None
    tester._proc.stdin = MagicMock()
    tester._proc.stdin.write = MagicMock()
    tester._proc.stdin.drain = AsyncMock(return_value=None)
    tester._lock = asyncio.Lock()
    tester._log_lock = asyncio.Lock()
    tester._recent_errors = {}
    tester._pending_futures = {}
    tester._stopping = False
    tester._consecutive_timeouts = 0
    tester._max_consecutive_timeouts = 2
    tester._restart_task = None
    tester._read_task = None
    tester._stderr_task = None
    tester._heartbeat_task = None
    return tester


async def _timeout_custom_result(awaitable, timeout):
    if timeout == 15.0:
        return await awaitable
    if timeout == 30.0:
        return await awaitable
    if hasattr(awaitable, "cancel"):
        awaitable.cancel()
    raise asyncio.TimeoutError


@pytest.mark.asyncio
async def test_custom_result_timeout_counts_and_restarts_daemon() -> None:
    tester = _make_custom_tester()
    custom = {"id": "chain-1", "outbounds": [{"type": "direct", "tag": "out"}]}

    with (
        patch.object(tester, "_ensure_process", new_callable=AsyncMock),
        patch.object(tester, "_restart_daemon", new_callable=AsyncMock) as restart,
        patch(
            "configstream.testers.go_tester.manager.safe_wait_for",
            side_effect=_timeout_custom_result,
        ),
    ):
        result = await tester.test_custom_configs([custom])

    assert result == {}
    assert tester._consecutive_timeouts == 1
    restart.assert_called_once()


@pytest.mark.asyncio
async def test_custom_result_timeout_disables_daemon_at_threshold() -> None:
    tester = _make_custom_tester()
    tester._consecutive_timeouts = 1
    custom = {"id": "chain-2", "outbounds": [{"type": "direct", "tag": "out"}]}

    with (
        patch.object(tester, "_ensure_process", new_callable=AsyncMock),
        patch.object(tester, "_restart_daemon", new_callable=AsyncMock) as restart,
        patch.object(tester, "close", new_callable=AsyncMock) as close,
        patch(
            "configstream.testers.go_tester.manager.safe_wait_for",
            side_effect=_timeout_custom_result,
        ),
    ):
        result = await tester.test_custom_configs([custom])

    assert result == {}
    assert tester._consecutive_timeouts == 2
    assert tester.available is False
    close.assert_called_once()
    restart.assert_not_called()
