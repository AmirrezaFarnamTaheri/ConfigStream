# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import asyncio
from collections import defaultdict
from urllib.parse import urlparse

import httpx
import pytest

from configstream.fetcher_worker import FetchResult
from configstream.pipeline import fetcher


@pytest.mark.asyncio
async def test_fetch_multiple_sources_enforces_per_host_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active: dict[str, int] = defaultdict(int)
    maximum: dict[str, int] = defaultdict(int)

    async def no_prewarm(_sources: list[str]) -> None:
        return None

    async def fake_fetch(
        _client: httpx.AsyncClient,
        source: str,
        **_kwargs: object,
    ) -> FetchResult:
        host = urlparse(source).hostname or "unknown"
        active[host] += 1
        maximum[host] = max(maximum[host], active[host])
        await asyncio.sleep(0.01)
        active[host] -= 1
        return FetchResult(
            success=True,
            source=source,
            content="ok",
            status_code=200,
        )

    monkeypatch.setattr(fetcher, "prewarm_dns_cache", no_prewarm)
    monkeypatch.setattr(fetcher, "fetch_from_source", fake_fetch)

    sources = [
        *(f"https://same.example/{index}" for index in range(6)),
        *(f"https://other.example/{index}" for index in range(3)),
    ]
    async with httpx.AsyncClient() as client:
        results = await fetcher.fetch_multiple_sources(
            sources,
            max_concurrent=9,
            per_host_limit=2,
            client=client,
            use_adaptive_timeout=False,
        )

    assert len(results) == len(sources)
    assert all(result.success for result in results.values())
    assert maximum["same.example"] == 2
    assert maximum["other.example"] == 2


@pytest.mark.asyncio
async def test_busy_host_does_not_hoard_global_fetch_slots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_same_started = asyncio.Event()
    release_first_same = asyncio.Event()
    other_started = asyncio.Event()

    async def no_prewarm(_sources: list[str]) -> None:
        return None

    async def fake_fetch(
        _client: httpx.AsyncClient,
        source: str,
        **_kwargs: object,
    ) -> FetchResult:
        if source == "https://same.example/0":
            first_same_started.set()
            await release_first_same.wait()
        if source.startswith("https://other.example/"):
            other_started.set()
        return FetchResult(
            success=True,
            source=source,
            content="ok",
            status_code=200,
        )

    monkeypatch.setattr(fetcher, "prewarm_dns_cache", no_prewarm)
    monkeypatch.setattr(fetcher, "fetch_from_source", fake_fetch)

    sources = [
        "https://same.example/0",
        "https://same.example/1",
        "https://same.example/2",
        "https://other.example/0",
    ]
    async with httpx.AsyncClient() as client:
        batch = asyncio.create_task(
            fetcher.fetch_multiple_sources(
                sources,
                max_concurrent=2,
                per_host_limit=1,
                client=client,
                use_adaptive_timeout=False,
            )
        )
        await first_same_started.wait()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        other_started_while_first_same_blocked = other_started.is_set()
        release_first_same.set()
        results = await batch

    assert len(results) == len(sources)
    assert other_started_while_first_same_blocked
