# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio

import pytest

from configstream.tools.dns_scanner.python.dnsscanner_lifecycle import (
    cancel_and_await_tasks as _cancel_and_await_tasks,
    kill_and_reap_processes as _kill_and_reap_processes,
)


@pytest.mark.asyncio
async def test_cancel_and_await_tasks_runs_task_finalizers():
    finalized = asyncio.Event()

    async def worker():
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
async def test_kill_and_reap_processes_waits_for_children():
    class Process:
        returncode = None

        def __init__(self):
            self.killed = False
            self.waited = 0

        def kill(self):
            self.killed = True
            self.returncode = -9

        async def wait(self):
            self.waited += 1
            return self.returncode

    process = Process()

    await _kill_and_reap_processes([process], timeout=0.1)

    assert process.killed is True
    assert process.waited == 1


@pytest.mark.asyncio
async def test_kill_and_reap_processes_reaps_already_exited_child():
    class Process:
        returncode = 0

        def __init__(self):
            self.killed = False
            self.waited = 0

        def kill(self):
            self.killed = True

        async def wait(self):
            self.waited += 1
            return self.returncode

    process = Process()

    await _kill_and_reap_processes([process], timeout=0.1)

    assert process.killed is False
    assert process.waited == 1
