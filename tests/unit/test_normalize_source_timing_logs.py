# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import sys
from pathlib import Path

from scripts.normalize_source_timing_logs import (
    SourceTiming,
    collect_timings,
    load_expected_sources,
    main,
    parse_source_timings,
    timing_coverage,
)


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


def test_parse_source_timings_handles_rich_source_column_and_wrapped_url() -> None:
    text = """
[05:39:40] INFO     Source Summary                               consumer.py:357
                    [https://raw.githubusercontent.com/MuRongPIG
                    /Proxy-Master/main/socks5.txt]:
                    Raw=500 Parsed=500 Tested=499 Working=9 Dur=731141ms
"""
    records = parse_source_timings(text, "pipeline_batch_8_part_1.log")
    assert len(records) == 1
    assert records[0].url == (
        "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks5.txt"
    )
    assert records[0].raw == 500
    assert records[0].duration_ms == 731141.0


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


def test_collect_timings_dedupes_rich_wrapped_url_variants(tmp_path: Path) -> None:
    log = tmp_path / "pipeline_batch_8_part_1.log"
    log.write_text(
        "\n".join(
            [
                "INFO Source Summary consumer.py:357 "
                "[https://raw.githubusercontent.com/MuRongPIG "
                "/Proxy-Master/main/socks5.txt]: Raw=500 Dur=1000ms",
                "INFO Source Summary consumer.py:357 "
                "[https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks5.txt]: "
                "Raw=500 Dur=2000ms",
            ]
        ),
        encoding="utf-8",
    )
    records = collect_timings([log])
    assert len(records) == 1
    assert records[0].duration_ms == 2000.0


def test_load_expected_sources_ignores_comments_and_invalid_lines(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "batch_1.txt"
    source_file.write_text(
        "# comment\nhttps://a.example/sub\nnot-a-url\nhttps://b.example/sub\n",
        encoding="utf-8",
    )
    assert load_expected_sources(str(tmp_path / "batch_*.txt")) == {
        "https://a.example/sub",
        "https://b.example/sub",
    }


def test_timing_coverage_normalizes_masked_query_variants() -> None:
    records = [
        SourceTiming(
            url="https://a.example/sub?token=[MASKED]",
            raw=10,
            duration_ms=1000.0,
            fetch_ms=None,
            source_log="a.log",
        ),
        SourceTiming(
            url="https://b.example/sub",
            raw=20,
            duration_ms=2000.0,
            fetch_ms=None,
            source_log="b.log",
        ),
    ]
    expected = {
        "https://a.example/sub?token=secret",
        "https://b.example/sub",
        "https://c.example/sub",
    }
    assert timing_coverage(records, expected) == 2 / 3


def test_timing_coverage_rejects_sparse_evidence() -> None:
    records = [
        SourceTiming(
            url=f"https://source-{index}.example/sub",
            raw=1,
            duration_ms=1000.0,
            fetch_ms=None,
            source_log="timing.log",
        )
        for index in range(7)
    ]
    expected = {f"https://source-{index}.example/sub" for index in range(10)}
    assert timing_coverage(records, expected) == 0.7


def test_main_removes_partial_outputs_when_coverage_fails(
    tmp_path: Path, monkeypatch
) -> None:
    log = tmp_path / "pipeline_batch_1_part_1.log"
    log.write_text(
        "Source Summary [https://a.example/sub]: Raw=1 Dur=1000ms\n",
        encoding="utf-8",
    )
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "batch_1.txt").write_text(
        "https://a.example/sub\nhttps://b.example/sub\n",
        encoding="utf-8",
    )
    normalized = tmp_path / "source_timing_normalized.log"
    evidence = tmp_path / "pipeline-evidence" / "source_timing.jsonl"
    normalized.write_text("stale\n", encoding="utf-8")
    evidence.parent.mkdir(parents=True)
    evidence.write_text("stale\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "normalize_source_timing_logs.py",
            "--pattern",
            str(tmp_path / "pipeline_batch_*.log"),
            "--sources-pattern",
            str(sources / "batch_*.txt"),
            "--min-coverage",
            "0.80",
            "--normalized-log",
            str(normalized),
            "--evidence",
            str(evidence),
        ],
    )

    assert main() == 1
    assert not normalized.exists()
    assert not evidence.exists()
