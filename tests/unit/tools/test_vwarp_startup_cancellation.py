# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest

from configstream.tools.vwarp import tunnel as tunnel_module
from configstream.tools.vwarp.tunnel import VwarpTunnel


@pytest.mark.asyncio
async def test_cancelled_startup_stops_spawned_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancellation after spawn must reap the child before propagating."""

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

    process = _Process()
    spawned = asyncio.Event()
    tunnel = VwarpTunnel("/tmp/vwarp")

    async def _build_command(
        bind_addr: str,
        port: int,
        config_override: dict[str, Any] | None = None,
    ) -> list[str]:
        del bind_addr, port, config_override
        return ["/tmp/vwarp"]

    async def _create_process(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        del args, kwargs
        spawned.set()
        return cast(asyncio.subprocess.Process, process)

    monkeypatch.setattr(tunnel, "_build_tunnel_command", _build_command)
    monkeypatch.setattr(tunnel_module.asyncio, "create_subprocess_exec", _create_process)

    startup = asyncio.create_task(tunnel._start_attempt("127.0.0.1", 8086))
    await spawned.wait()
    await asyncio.sleep(0)
    startup.cancel()

    with pytest.raises(asyncio.CancelledError):
        await startup

    assert process.terminated is True
    assert process.waited == 1
    assert tunnel._proc is None
