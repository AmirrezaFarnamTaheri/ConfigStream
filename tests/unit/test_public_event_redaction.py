# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

import pytest

from configstream.event_stream import EventStream


@pytest.mark.asyncio
async def test_public_event_persistence_redacts_source_and_block_reason(
    tmp_path: Path,
) -> None:
    stream = EventStream(tmp_path)
    source = "https://provider.example/subscription?token=private-value"
    stream.emit("fetch_success", f"Fetched 4 proxies from {source} (Fetch: 1.2s)")
    stream.emit("fetch_blocked", f"Blocked source {source}: detector raw detail")
    await stream.aclose()

    payload = (tmp_path / "pipeline_events.jsonl").read_text(encoding="utf-8")
    assert "provider.example" not in payload
    assert "private-value" not in payload
    assert "detector raw detail" not in payload

    records = [json.loads(line) for line in payload.splitlines()]
    assert records[0]["message"] == "Fetched 4 proxies from [source] (Fetch: 1.2s)"
    assert records[1]["message"] == "Source blocked by anomaly policy."
