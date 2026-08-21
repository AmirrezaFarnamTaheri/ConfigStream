# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from configstream.security_validator import SecurityValidator
from scripts.normalize_source_timing_logs import (
    SourceTiming,
    collect_timings,
    infer_shard_parts,
    load_expected_sources,
    load_expected_sources_by_batch,
    main,
    parse_source_timings,
    resolve_timings,
    source_id_for_url,
    timing_coverage,
    timing_resolution_counts,
    write_outputs,
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


def test_resolve_timings_recovers_canonical_url_from_sanitized_shard_log(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    canonical = (
        "https://raw.githubusercontent.com/example/"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ/main/sub.txt"
    )
    (sources / "batch_1.txt").write_text(canonical + "\n", encoding="utf-8")
    masked = SecurityValidator.sanitize_log_message(canonical)
    assert masked != canonical
    assert "[BASE64]" in masked

    log = tmp_path / "pipeline_batch_1_part_1.log"
    log.write_text(
        f"INFO Source Summary [{masked}]: Raw=17 Dur=2500ms\n",
        encoding="utf-8",
    )
    raw_records = parse_source_timings(log.read_text(), log.name)
    sources_by_batch = load_expected_sources_by_batch(str(sources / "batch_*.txt"))
    parts = infer_shard_parts([log], configured_parts=1)
    assert timing_resolution_counts(raw_records, sources_by_batch, parts) == (1, 1)

    records = resolve_timings(raw_records, sources_by_batch, parts)
    assert len(records) == 1
    assert records[0].url == canonical
    assert source_id_for_url(records[0].url) == source_id_for_url(canonical)

    normalized = tmp_path / "source_timing_normalized.log"
    evidence = tmp_path / "pipeline-evidence" / "source_timing.jsonl"
    write_outputs(records, normalized, evidence)
    payload = json.loads(evidence.read_text(encoding="utf-8").strip())
    assert payload["source_id"] == source_id_for_url(canonical)
    assert payload["source_url"] == masked


def test_infer_shard_parts_preserves_configured_count_when_highest_log_missing(
    tmp_path: Path,
) -> None:
    logs = [tmp_path / f"pipeline_batch_1_part_{part}.log" for part in (1, 2, 3)]
    assert infer_shard_parts(logs, configured_parts=4) == 4


def test_infer_shard_parts_rejects_non_positive_configured_count(
    tmp_path: Path,
) -> None:
    log = tmp_path / "pipeline_batch_1_part_1.log"
    with pytest.raises(ValueError, match="must be positive"):
        infer_shard_parts([log], configured_parts=0)


def test_infer_shard_parts_rejects_out_of_range_observed_part(tmp_path: Path) -> None:
    log = tmp_path / "pipeline_batch_1_part_5.log"
    with pytest.raises(ValueError, match="outside the configured shard count"):
        infer_shard_parts([log], configured_parts=4)


def test_resolution_coverage_rejects_ambiguous_sanitizer_collision(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    first = "https://raw.githubusercontent.com/a/ABCDEFGHIJKLMNOPQRSTUV/main/sub.txt"
    second = "https://raw.githubusercontent.com/b/ABCDEFGHIJKLMNOPQRSTUV/main/sub.txt"
    (sources / "batch_1.txt").write_text(
        f"{first}\n{second}\n",
        encoding="utf-8",
    )
    masked = SecurityValidator.sanitize_log_message(first)
    assert masked == SecurityValidator.sanitize_log_message(second)

    record = SourceTiming(
        url=masked,
        raw=1,
        duration_ms=1000.0,
        fetch_ms=None,
        source_log="pipeline_batch_1_part_1.log",
    )
    sources_by_batch = load_expected_sources_by_batch(str(sources / "batch_*.txt"))

    assert timing_resolution_counts([record], sources_by_batch, 1) == (0, 1)
    assert resolve_timings([record], sources_by_batch, 1) == []


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
        "Source Summary [https://unknown.example/sub]: Raw=1 Dur=1000ms\n",
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
            "--parts",
            "1",
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
