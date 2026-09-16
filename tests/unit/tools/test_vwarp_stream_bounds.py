# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
from unittest.mock import AsyncMock

import pytest

from configstream.tools.vwarp import tunnel as tunnel_module
from configstream.tools.vwarp.tunnel import VwarpTunnel


class _ChunkStream:
    def __init__(self, chunks: list[bytes]):
        self._chunks = list(chunks)
        self.read_sizes: list[int] = []

    async def read(self, size: int) -> bytes:
        self.read_sizes.append(size)
        if not self._chunks:
            return b""
        chunk = self._chunks.pop(0)
        if len(chunk) <= size:
            return chunk
        self._chunks.insert(0, chunk[size:])
        return chunk[:size]


class _Process:
    def __init__(self) -> None:
        self.returncode: int | None = None
        self.stdout = _ChunkStream([b"x" * 9000, b""])
        self.stderr = _ChunkStream([b"warning", b""])

    async def wait(self) -> int:
        return 0 if self.returncode is None else self.returncode

    def terminate(self) -> None:
        self.returncode = 0

    def kill(self) -> None:
        self.returncode = -9


@pytest.mark.asyncio
async def test_start_drains_child_pipes_in_bounded_chunks_before_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _Process()
    tunnel = VwarpTunnel("/trusted/vwarp")
    real_sleep = asyncio.sleep

    async def fast_sleep(_delay: float) -> None:
        await real_sleep(0)

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
    monkeypatch.setattr(tunnel_module.asyncio, "sleep", fast_sleep)
    monkeypatch.setattr(tunnel, "_wait_for_port", AsyncMock(return_value=True))

    assert await tunnel._start_attempt("127.0.0.1", 8086) is True
    await real_sleep(0)

    assert process.stdout.read_sizes
    assert process.stderr.read_sizes
    assert max(process.stdout.read_sizes) == 4096
    assert max(process.stderr.read_sizes) == 4096

    process.returncode = 0
    await tunnel.stop()
