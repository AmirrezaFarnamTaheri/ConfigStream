# SPDX-License-Identifier: AGPL-3.0-or-later
from unittest.mock import AsyncMock

import pytest

from configstream.intelligence.washer.core import ProxyWasher


class _OpenWriter:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return None


@pytest.mark.asyncio
async def test_managed_downloaded_vwarp_uses_runtime_state_before_binary_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A manager-launched non-PATH binary remains eligible for socket probing."""
    washer = ProxyWasher("[]")
    writer = _OpenWriter()
    open_connection = AsyncMock(return_value=(object(), writer))

    monkeypatch.setenv("USE_VWARP_TUNNEL", "true")
    monkeypatch.setattr(washer, "_has_vwarp_binary", lambda: False)
    monkeypatch.setattr("asyncio.open_connection", open_connection)

    assert await washer.is_vwarp_available_async() is True
    open_connection.assert_awaited_once()
    assert writer.closed is True


@pytest.mark.asyncio
async def test_failed_managed_startup_disables_vwarp_without_socket_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    washer = ProxyWasher("[]")
    open_connection = AsyncMock()

    monkeypatch.setenv("USE_VWARP_TUNNEL", "false")
    monkeypatch.setattr(washer, "_has_vwarp_binary", lambda: True)
    monkeypatch.setattr("asyncio.open_connection", open_connection)

    assert await washer.is_vwarp_available_async() is False
    open_connection.assert_not_awaited()


@pytest.mark.asyncio
async def test_unmanaged_vwarp_still_requires_binary_and_live_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    washer = ProxyWasher("[]")
    open_connection = AsyncMock()

    monkeypatch.delenv("USE_VWARP_TUNNEL", raising=False)
    monkeypatch.setattr(washer, "_has_vwarp_binary", lambda: False)
    monkeypatch.setattr("asyncio.open_connection", open_connection)

    assert await washer.is_vwarp_available_async() is False
    open_connection.assert_not_awaited()
