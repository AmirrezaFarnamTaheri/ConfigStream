# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from configstream.tools.vwarp import scanner as scanner_module


def test_scan_endpoint_parser_handles_ipv4_ipv6_and_port_bounds() -> None:
    assert scanner_module._parse_endpoint("1.2.3.4") == ("1.2.3.4", 2408)
    assert scanner_module._parse_endpoint("1.2.3.4:443") == ("1.2.3.4", 443)
    assert scanner_module._parse_endpoint("2001:db8::1") == ("2001:db8::1", 2408)
    assert scanner_module._parse_endpoint("[2001:db8::1]:8443") == (
        "2001:db8::1",
        8443,
    )
    assert scanner_module._parse_endpoint("1::2::3") is None
    assert scanner_module._parse_endpoint("1.2.3.4:0") is None
    assert scanner_module._parse_endpoint("1.2.3.4:65536") is None
    assert scanner_module._parse_endpoint("1.2.3.4:not-a-port") is None


class _ScannerProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None
        self.killed = False
        self.waited = False

    async def communicate(self) -> tuple[bytes, bytes]:
        await asyncio.Event().wait()
        return b"", b""

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    async def wait(self) -> int:
        self.waited = True
        return -9


def _enable_scanner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        scanner_module,
        "AppSettings",
        lambda: SimpleNamespace(ALLOW_ACTIVE_SCANNING=True, FORCE_SCANNER=False),
    )
    monkeypatch.setattr(scanner_module, "verify_binary", AsyncMock(return_value=True))


@pytest.mark.asyncio
async def test_scan_timeout_kills_and_reaps_child(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_scanner(monkeypatch)
    process = _ScannerProcess()
    monkeypatch.setattr(
        scanner_module.asyncio,
        "create_subprocess_exec",
        AsyncMock(return_value=process),
    )

    async def fake_wait_for(awaitable, timeout: float):
        if timeout == 60:
            close = getattr(awaitable, "close", None)
            if close is not None:
                close()
            raise asyncio.TimeoutError
        return await awaitable

    monkeypatch.setattr(scanner_module, "safe_wait_for", fake_wait_for)

    assert await scanner_module.scan_endpoints("/trusted/vwarp") == []
    assert process.killed is True
    assert process.waited is True


@pytest.mark.asyncio
async def test_scan_cancellation_kills_and_reaps_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_scanner(monkeypatch)
    process = _ScannerProcess()
    monkeypatch.setattr(
        scanner_module.asyncio,
        "create_subprocess_exec",
        AsyncMock(return_value=process),
    )

    async def fake_wait_for(awaitable, timeout: float):
        if timeout == 60:
            close = getattr(awaitable, "close", None)
            if close is not None:
                close()
            raise asyncio.CancelledError
        return await awaitable

    monkeypatch.setattr(scanner_module, "safe_wait_for", fake_wait_for)

    with pytest.raises(asyncio.CancelledError):
        await scanner_module.scan_endpoints("/trusted/vwarp")

    assert process.killed is True
    assert process.waited is True
