# SPDX-License-Identifier: AGPL-3.0-or-later
from unittest.mock import AsyncMock

import pytest

from configstream.tools.vwarp import tunnel as tunnel_module
from configstream.tools.vwarp.tunnel import VwarpTunnel


@pytest.mark.asyncio
async def test_start_reaps_exited_child_before_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    class ExitedProcess:
        returncode = 1

        async def wait(self) -> int:
            return self.returncode

    tunnel = VwarpTunnel("/trusted/vwarp")
    tunnel._proc = ExitedProcess()  # type: ignore[assignment]

    monkeypatch.setattr(tunnel_module, "verify_binary", AsyncMock(return_value=True))
    retry = AsyncMock(return_value=True)
    monkeypatch.setattr(tunnel, "_start_attempt", retry)

    assert await tunnel.start() is True
    retry.assert_awaited_once()


@pytest.mark.asyncio
async def test_immediate_child_failure_clears_process_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailedProcess:
        returncode = 1

        async def communicate(self):
            return b"", b"startup failed"

        async def wait(self) -> int:
            return self.returncode

    tunnel = VwarpTunnel("/trusted/vwarp")
    process = FailedProcess()

    monkeypatch.setattr(
        tunnel,
        "_build_tunnel_command",
        AsyncMock(return_value=["/trusted/vwarp", "--bind", "127.0.0.1:8086"]),
    )
    monkeypatch.setattr(
        tunnel_module.asyncio,
        "create_subprocess_exec",
        AsyncMock(return_value=process),
    )
    monkeypatch.setattr(tunnel_module.asyncio, "sleep", AsyncMock(return_value=None))

    assert await tunnel._start_attempt("127.0.0.1", 8086) is False
    assert tunnel._proc is None
