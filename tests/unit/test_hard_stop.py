# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
from types import SimpleNamespace

import pytest

from configstream.hard_stop import HardStopWatcher


class _FakeProc:
    def __init__(self) -> None:
        self.returncode: int | None = None
        self.killed = False
        self.wait_called = False

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    async def wait(self) -> int:
        self.wait_called = True
        return -9


@pytest.mark.asyncio
async def test_hard_stop_kills_hung_tester_process() -> None:
    proc = _FakeProc()
    go_tester = SimpleNamespace(_proc=proc)

    class _HungTester:
        def __init__(self) -> None:
            self.go_tester = go_tester

        async def close(self) -> None:
            await asyncio.sleep(0.2)

    watcher = HardStopWatcher(grace_seconds=0.01, flush_timeout_seconds=0.1)
    tester = _HungTester()

    await watcher.stop_tester(tester)

    assert proc.killed is True
    assert proc.wait_called is True
    assert tester.go_tester._proc is None


@pytest.mark.asyncio
async def test_hard_stop_kills_process_when_close_raises() -> None:
    proc = _FakeProc()
    go_tester = SimpleNamespace(_proc=proc)

    class _BrokenTester:
        def __init__(self) -> None:
            self.go_tester = go_tester

        async def close(self) -> None:
            # Simulate a close implementation that loses its public process handle
            # before surfacing the failure. HardStopWatcher must retain ownership.
            self.go_tester._proc = None
            raise RuntimeError("close failed")

    tester = _BrokenTester()
    watcher = HardStopWatcher(grace_seconds=0.1, flush_timeout_seconds=0.1)

    await watcher.stop_tester(tester)

    assert proc.killed is True
    assert proc.wait_called is True
