# SPDX-License-Identifier: AGPL-3.0-or-later
"""Production regression for RFC HTTP-date Retry-After handling."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from configstream.config import AppSettings
from configstream.pipeline.fetcher import fetch_from_source


@pytest.mark.asyncio
async def test_fetch_from_source_honors_http_date_retry_after_with_bound() -> None:
    client = AsyncMock(spec=httpx.AsyncClient)
    settings = AppSettings()
    settings.FETCH_VALIDATE_DNS = False

    response = AsyncMock()
    response.status_code = 429
    response.headers = {
        "Retry-After": format_datetime(
            datetime.now(timezone.utc) + timedelta(minutes=2), usegmt=True
        )
    }
    stream = AsyncMock()
    stream.__aenter__.return_value = response
    client.stream.return_value = stream

    with patch("asyncio.sleep", new_callable=AsyncMock) as sleep:
        result = await fetch_from_source(
            client,
            "https://example.com/subscription",
            max_retries=2,
            app_settings=settings,
        )

    assert result.success is False
    assert "Rate limited" in result.error
    assert sleep.await_count >= 1
    assert all(call.args[0] == 30.0 for call in sleep.await_args_list)
