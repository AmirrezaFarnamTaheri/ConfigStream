# SPDX-License-Identifier: AGPL-3.0-or-later
"""Producer accounting checks for queue pressure versus source failure."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock

import pytest

from configstream.config import AppSettings
from configstream.pipeline.producer import _report_source_backpressure


@pytest.mark.asyncio
async def test_backpressure_accounting_does_not_penalize_source_health() -> None:
    loop = asyncio.get_running_loop()
    quality = MagicMock()

    await _report_source_backpressure(
        loop,
        quality,
        AppSettings(),
        "https://example.com/sub.txt",
        dropped=42,
        duration_ms=12.5,
    )

    quality.report_failure.assert_not_called()
    quality.record_run.assert_called_once()
    source, payload = quality.record_run.call_args.args

    assert source == "https://example.com/sub.txt"
    assert payload["duration_ms"] == 12.5
    assert payload["fetched_count"] == 0
    assert payload["working_count"] == 0
    assert json.loads(payload["failure_modes_json"]) == {"backpressure_drop": 42}
