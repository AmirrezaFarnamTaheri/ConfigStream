# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path

import pytest

from configstream.history.tracker import ProxyHistoryTracker
from configstream.intelligence.washer.core import ProxyWasher
from configstream.pipeline_core.output_handler import generate_pipeline_outputs
from configstream.pipeline_core.stats import PipelineStats


@pytest.mark.asyncio
async def test_generate_pipeline_outputs_creates_frontend_data_files(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    stats = PipelineStats()
    history = ProxyHistoryTracker(tmp_path / "history.db")
    washer = ProxyWasher("[]")
    washer.clean_ips = [("162.159.192.1", 2408), ("162.159.193.5", 2408)]

    try:
        await generate_pipeline_outputs([], out_dir, stats, history, washer=washer)
    finally:
        history.close()

    # Required for lab.html auto-discovery
    clean_ips_path = out_dir / "data" / "clean_ips.json"
    assert clean_ips_path.exists()
    clean_ips = json.loads(clean_ips_path.read_text(encoding="utf-8"))
    assert isinstance(clean_ips, list)
    assert clean_ips and clean_ips[0]["ip"] == "162.159.192.1"

    # Required for analytics/dashboard pages
    assert (out_dir / "data" / "proxy_history_viz.json").exists()
    assert (out_dir / "data" / "active_proxy_trend.json").exists()
    assert (out_dir / "data" / "evasion_trend.json").exists()

    # Canonical stats source for the frontend
    assert (out_dir / "metadata.json").exists()
