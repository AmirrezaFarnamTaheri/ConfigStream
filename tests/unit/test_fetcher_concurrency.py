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
async def test_fetch_multiple_sources_enforces_per_host_limit(monkeypatch) -> None:
    active: dict[str, int] = defaultdict(int)
    maximum: dict[str, int] = defaultdict(int)

    async def no_prewarm(_sources) -> None:
        return None

    async def fake_fetch(_client, source: str, **_kwargs) -> FetchResult:
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
