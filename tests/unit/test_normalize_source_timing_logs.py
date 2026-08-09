# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

from scripts.normalize_source_timing_logs import collect_timings, parse_source_timings


def test_parse_source_timings_recovers_rich_wrapped_summary() -> None:
    text = """
2026-08-09 01:00:00 INFO     Source Summary
                             [https://raw.githubusercontent.com/acme/repo/main/sub.txt]:
                             Raw=500 Parsed=500 Tested=500 Working=1
                             Fetch=631.2ms Dur=199631ms
"""
    records = parse_source_timings(text, "pipeline_batch_7_part_2.log")
    assert len(records) == 1
    assert records[0].url == "https://raw.githubusercontent.com/acme/repo/main/sub.txt"
    assert records[0].raw == 500
    assert records[0].fetch_ms == 631.2
    assert records[0].duration_ms == 199631.0


def test_parse_source_timings_does_not_borrow_duration_from_next_record() -> None:
    text = """
INFO Source Summary [https://broken.example/sub]: Raw=9
INFO Source Summary [https://good.example/sub]: Raw=10 Dur=2500ms
"""
    records = parse_source_timings(text, "pipeline_batch_1_part_1.log")
    assert [(record.url, record.duration_ms) for record in records] == [
        ("https://good.example/sub", 2500.0)
    ]


def test_collect_timings_keeps_slowest_duplicate_observation(tmp_path: Path) -> None:
    first = tmp_path / "pipeline_batch_1_part_1.log"
    second = tmp_path / "pipeline_batch_1_part_2.log"
    first.write_text(
        "Source Summary [https://example.com/sub]: Raw=10 Dur=1000ms\n",
        encoding="utf-8",
    )
    second.write_text(
        "Source Summary\n [https://example.com/sub]: Raw=10 Dur=2500ms\n",
        encoding="utf-8",
    )
    records = collect_timings([first, second])
    assert len(records) == 1
    assert records[0].duration_ms == 2500.0
    assert records[0].source_log == second.name
