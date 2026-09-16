# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
from typing import Any, cast

import pytest

from configstream.testers.go_tester import process as process_module
from configstream.testers.go_tester.process import ProcessManager


class _Process:
    def __init__(self) -> None:
        self.returncode: int | None = None
        self.terminated = False
        self.killed = False
        self.waited = 0

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        self.waited += 1
        self.returncode = -9 if self.killed else 0
        return self.returncode


def _manager_with(process: _Process) -> ProcessManager:
    manager = ProcessManager(binary_name="/definitely/missing/configstream-tester")
    manager._proc = cast(asyncio.subprocess.Process, process)
    return manager


@pytest.mark.asyncio
async def test_stop_cancellation_kills_reaps_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _Process()
    manager = _manager_with(process)
    calls = 0

    async def fake_wait_for(awaitable: Any, timeout: float) -> Any:
        nonlocal calls
        calls += 1
        if calls == 1:
            close = getattr(awaitable, "close", None)
            if close is not None:
                close()
            raise asyncio.CancelledError
        return await awaitable

    monkeypatch.setattr(process_module.asyncio, "wait_for", fake_wait_for)

    with pytest.raises(asyncio.CancelledError):
        await manager.stop()

    assert process.terminated is True
    assert process.killed is True
    assert process.waited == 1
    assert manager._proc is None


@pytest.mark.asyncio
async def test_stop_timeout_kills_and_reaps(monkeypatch: pytest.MonkeyPatch) -> None:
    process = _Process()
    manager = _manager_with(process)
    calls = 0

    async def fake_wait_for(awaitable: Any, timeout: float) -> Any:
        nonlocal calls
        calls += 1
        if calls == 1:
            close = getattr(awaitable, "close", None)
            if close is not None:
                close()
            raise asyncio.TimeoutError
        return await awaitable

    monkeypatch.setattr(process_module.asyncio, "wait_for", fake_wait_for)

    await manager.stop()

    assert process.terminated is True
    assert process.killed is True
    assert process.waited == 1
    assert manager._proc is None


@pytest.mark.asyncio
async def test_stop_retains_handle_when_reap_cannot_confirm_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _Process()
    manager = _manager_with(process)

    async def always_timeout(awaitable: Any, timeout: float) -> Any:
        close = getattr(awaitable, "close", None)
        if close is not None:
            close()
        raise asyncio.TimeoutError

    monkeypatch.setattr(process_module.asyncio, "wait_for", always_timeout)

    await manager.stop()

    assert process.terminated is True
    assert process.killed is True
    assert process.returncode is None
    assert manager._proc is cast(asyncio.subprocess.Process, process)
