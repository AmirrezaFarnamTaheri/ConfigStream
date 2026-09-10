# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path


def test_main_records_shard_download_only_after_lineage_count_matches_matrix() -> None:
    workflow = Path(".github/workflows/main.yml").read_text(encoding="utf-8")

    assert 'shard_status="${{ steps.shard_download.outcome }}"' in workflow
    assert 'Path("artifacts").rglob("shard_lineage.json")' in workflow
    assert "shard artifact lineage mismatch" in workflow
    record = 'record --name shard-download --status "$shard_status"'
    assert record in workflow

    record_step = workflow.split("      - name: Record artifact downloads", 1)[1].split(
        "      - name: Restore available artifacts", 1
    )[0]
    assert record_step.index("shard artifact lineage mismatch") < record_step.index(record)


def test_geoip_prerequisite_is_geoip_only_and_retained_for_reruns() -> None:
    workflow = Path(".github/workflows/main.yml").read_text(encoding="utf-8")

    assert "python -m configstream.cli update-databases --geoip-only" in workflow
    geoip_section = workflow.split("  setup_geoip:", 1)[1].split("  setup_matrix:", 1)[
        0
    ]
    assert "retention-days: 30" in geoip_section
