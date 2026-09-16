# SPDX-License-Identifier: AGPL-3.0-or-later
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from configstream.pipeline import fetcher as fetcher_module
from configstream.pipeline.fetcher import HttpFetcher


@pytest.mark.asyncio
async def test_http_fetcher_default_owns_hardened_client(monkeypatch: pytest.MonkeyPatch) -> None:
    managed_client = object()
    expected = object()

    @asynccontextmanager
    async def managed():
        yield managed_client

    fetch = AsyncMock(return_value=expected)
    monkeypatch.setattr(fetcher_module, "get_client", managed)
    monkeypatch.setattr(fetcher_module, "fetch_from_source", fetch)

    result = await HttpFetcher().fetch("https://example.com/source")

    assert result is expected
    fetch.assert_awaited_once_with(
        managed_client,
        "https://example.com/source",
        app_settings=None,
        breaker_manager=None,
        timeout_tracker=None,
    )


@pytest.mark.asyncio
async def test_http_fetcher_preserves_injected_client(monkeypatch: pytest.MonkeyPatch) -> None:
    injected = object()
    expected = object()
    fetch = AsyncMock(return_value=expected)
    monkeypatch.setattr(fetcher_module, "fetch_from_source", fetch)

    result = await HttpFetcher(client=injected).fetch("https://example.com/source")

    assert result is expected
    fetch.assert_awaited_once_with(
        injected,
        "https://example.com/source",
        app_settings=None,
        breaker_manager=None,
        timeout_tracker=None,
    )
