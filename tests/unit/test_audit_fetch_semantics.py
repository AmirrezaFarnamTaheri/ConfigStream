# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from configstream.config import AppSettings
from configstream.pipeline.fetcher import fetch_from_source
from scripts.aggregate_shard_health import source_summary_counts


def _settings() -> AppSettings:
    settings = AppSettings()
    settings.FETCH_VALIDATE_DNS = False
    return settings


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 204])
async def test_empty_success_body_is_not_a_successful_source(status: int) -> None:
    client = AsyncMock(spec=httpx.AsyncClient)
    response = AsyncMock()
    response.status_code = status
    response.headers = {}

    async def body():
        yield b" \n\t"

    response.aiter_bytes = lambda: body()
    stream = AsyncMock()
    stream.__aenter__.return_value = response
    client.stream.return_value = stream

    result = await fetch_from_source(
        client,
        "https://example.com/empty",
        app_settings=_settings(),
        max_retries=1,
    )

    assert result.success is False
    assert result.status_code == status
    assert result.error == "Empty content"


@pytest.mark.asyncio
async def test_retry_after_http_date_is_honored_by_production_fetcher() -> None:
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=12)
    header = retry_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
    client = AsyncMock(spec=httpx.AsyncClient)
    response = AsyncMock()
    response.status_code = 429
    response.headers = {"Retry-After": header}
    stream = AsyncMock()
    stream.__aenter__.return_value = response
    client.stream.return_value = stream

    with patch("asyncio.sleep", new_callable=AsyncMock) as sleep:
        result = await fetch_from_source(
            client,
            "https://example.com/limited",
            app_settings=_settings(),
            max_retries=1,
        )

    assert result.success is False
    assert result.error == "Max retries exceeded: Rate limited"
    assert sleep.await_count == 1
    delay = float(sleep.await_args.args[0])
    assert 8.0 <= delay <= 12.5


def test_release_coverage_prefers_usable_sources_over_http_success(tmp_path) -> None:
    log = tmp_path / "pipeline.log"
    log.write_text(
        "\n".join(
            [
                "Fetch Summary: 11/12 sources successful. Total data fetched: 12.00 KB",
                "Usable Source Summary: 4/12 sources produced accepted records.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    usable, transport_success, attempted = source_summary_counts(
        log,
        source_count=12,
        fallback_fetched_sources=12,
    )

    assert (usable, transport_success, attempted) == (4, 11, 12)


def test_usable_source_count_is_bounded_by_transport_and_attempts(tmp_path) -> None:
    log = tmp_path / "pipeline.log"
    log.write_text(
        "Fetch Summary: 3/5 sources successful.\n"
        "Usable Source Summary: 99/5 sources produced accepted records.\n",
        encoding="utf-8",
    )

    assert source_summary_counts(
        log,
        source_count=5,
        fallback_fetched_sources=5,
    ) == (3, 3, 5)
