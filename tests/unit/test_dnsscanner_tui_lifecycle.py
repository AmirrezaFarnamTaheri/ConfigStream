# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio

import pytest

from configstream.tools.dns_scanner.python.dnsscanner_lifecycle import (
    cancel_and_await_tasks as _cancel_and_await_tasks,
    kill_and_reap_processes as _kill_and_reap_processes,
)


@pytest.mark.asyncio
async def test_cancel_and_await_tasks_runs_task_finalizers() -> None:
    finalized = asyncio.Event()

    async def worker() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            finalized.set()

    task = asyncio.create_task(worker())
    await asyncio.sleep(0)

    await _cancel_and_await_tasks([task])

    assert task.done()
    assert finalized.is_set()


@pytest.mark.asyncio
async def test_kill_and_reap_processes_waits_for_children() -> None:
    class Process:
        returncode = None

        def __init__(self) -> None:
            self.killed = False
            self.waited = 0

        def kill(self) -> None:
            self.killed = True
            self.returncode = -9

        async def wait(self) -> int | None:
            self.waited += 1
            return self.returncode

    process = Process()

    await _kill_and_reap_processes([process], timeout=0.1)

    assert process.killed is True
    assert process.waited == 1


@pytest.mark.asyncio
async def test_kill_and_reap_processes_reaps_already_exited_child() -> None:
    class Process:
        returncode = 0

        def __init__(self) -> None:
            self.killed = False
            self.waited = 0

        def kill(self) -> None:
            self.killed = True

        async def wait(self) -> int | None:
            self.waited += 1
            return self.returncode

    process = Process()

    await _kill_and_reap_processes([process], timeout=0.1)

    assert process.killed is False
    assert process.waited == 1



def test_tui_initialization_defers_unsupported_slipstream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from configstream.tools.dns_scanner.python import dnsscanner_tui

    monkeypatch.setattr(dnsscanner_tui.platform, "system", lambda: "Linux")
    monkeypatch.setattr(dnsscanner_tui.platform, "machine", lambda: "armv7l")

    app = dnsscanner_tui.DNSScannerTUI()

    assert app.slipstream_path == ""
    assert app.slipstream_manager.is_supported() is False
    assert app.slipstream_manager.get_download_url() is None
    with pytest.raises(RuntimeError, match="Unsupported platform"):
        app.slipstream_manager.get_executable_path()
