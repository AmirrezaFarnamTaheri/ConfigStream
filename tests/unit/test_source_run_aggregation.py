# SPDX-License-Identifier: AGPL-3.0-or-later
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from configstream.source_quality import SourceQualityTracker
from configstream.source_run_aggregation import record_source_chunk


def _fingerprint_path(tmp_path: Path, source: str) -> Path:
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return tmp_path / "data" / "fingerprints" / f"{source_hash}.json"


def test_source_chunks_aggregate_out_of_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "quality.db"
    tracker = SourceQualityTracker(db_path=db_path)
    source = "https://example.com/source.txt"

    record_source_chunk(
        tracker,
        source,
        "run-1",
        2,
        20,
        5,
        15.0,
        {"US": 5},
        {"duplicate": 1},
        "pipeline",
        123,
        [("b.example", 443)],
    )
    record_source_chunk(
        tracker,
        source,
        "run-1",
        1,
        20,
        10,
        25.0,
        {"NL": 10},
        {"invalid": 2},
        "pipeline",
        123,
        [("a.example", 443)],
    )

    state = tracker.get_source_state(source)
    assert state is not None
    assert state[0] == "active"
    assert state[2] == 0
    assert state[3] == pytest.approx(37.5)
    assert state[4] == 40
    assert state[5] == 15

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT duration_ms, fetched_count, working_count,
                   geoip_json, failure_modes_json
            FROM source_runs WHERE url = ?
            """,
            (source,),
        ).fetchone()
        count_row = conn.execute(
            "SELECT COUNT(*) FROM source_runs WHERE url = ?", (source,)
        ).fetchone()

    assert count_row is not None
    assert count_row[0] == 1
    assert row is not None
    assert row[0] == pytest.approx(40.0)
    assert row[1:3] == (40, 15)
    assert json.loads(row[3]) == {"NL": 10, "US": 5}
    assert json.loads(row[4]) == {"duplicate": 1, "invalid": 2}

    fingerprint = json.loads(_fingerprint_path(tmp_path, source).read_text())
    assert fingerprint["timestamp"] == 123
    assert fingerprint["proxies"] == [
        ["a.example", 443],
        ["b.example", 443],
    ]


def test_failed_run_counts_once_and_chunk_replay_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "quality.db"
    tracker = SourceQualityTracker(db_path=db_path)
    source = "https://example.com/flaky.txt"
    tracker.update(source, fetched=10, working=0, diversity=0.0)

    record_source_chunk(
        tracker,
        source,
        "run-2",
        2,
        5,
        0,
        2.0,
        {},
        {"test_failed": 5},
        "pipeline",
        456,
        [("b.example", 443)],
    )
    record_source_chunk(
        tracker,
        source,
        "run-2",
        1,
        5,
        0,
        3.0,
        {},
        {"test_failed": 5},
        "pipeline",
        456,
        [("a.example", 443)],
    )

    failed_state = tracker.get_source_state(source)
    assert failed_state is not None
    assert failed_state[2] == 2
    assert failed_state[4:6] == (10, 0)

    record_source_chunk(
        tracker,
        source,
        "run-2",
        1,
        5,
        3,
        4.0,
        {"DE": 3},
        {"test_failed": 2},
        "pipeline",
        456,
        [("c.example", 443)],
    )

    replayed_state = tracker.get_source_state(source)
    assert replayed_state is not None
    assert replayed_state[0] == "active"
    assert replayed_state[2] == 0
    assert replayed_state[3] == pytest.approx(30.0)
    assert replayed_state[4:6] == (10, 3)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT duration_ms, fetched_count, working_count FROM source_runs WHERE url = ?",
            (source,),
        ).fetchone()
        count_row = conn.execute(
            "SELECT COUNT(*) FROM source_runs WHERE url = ?", (source,)
        ).fetchone()

    assert count_row is not None
    assert count_row[0] == 1
    assert row is not None
    assert row[0] == pytest.approx(6.0)
    assert row[1:] == (10, 3)


def test_new_run_replaces_previous_fingerprint_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    tracker = SourceQualityTracker(db_path=tmp_path / "quality.db")
    source = "https://example.com/rotating.txt"

    record_source_chunk(
        tracker,
        source,
        "run-a",
        1,
        2,
        2,
        1.0,
        {"US": 2},
        {},
        "pipeline",
        100,
        [("a.example", 443), ("b.example", 443)],
    )
    record_source_chunk(
        tracker,
        source,
        "run-b",
        1,
        1,
        1,
        1.0,
        {"NL": 1},
        {},
        "pipeline",
        200,
        [("c.example", 443)],
    )

    fingerprint = json.loads(_fingerprint_path(tmp_path, source).read_text())
    assert fingerprint["timestamp"] == 200
    assert fingerprint["proxies"] == [["c.example", 443]]

    with sqlite3.connect(tmp_path / "quality.db") as conn:
        count_row = conn.execute(
            "SELECT COUNT(*) FROM source_runs WHERE url = ?", (source,)
        ).fetchone()
    assert count_row is not None
    assert count_row[0] == 2


def test_empty_run_clears_previous_fingerprint_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    tracker = SourceQualityTracker(db_path=tmp_path / "quality.db")
    source = "https://example.com/emptied.txt"

    record_source_chunk(
        tracker,
        source,
        "run-a",
        1,
        1,
        1,
        1.0,
        {"US": 1},
        {},
        "pipeline",
        100,
        [("a.example", 443)],
    )
    record_source_chunk(
        tracker,
        source,
        "run-b",
        1,
        0,
        0,
        2.0,
        {},
        {"parse_empty": 4},
        "pipeline",
        200,
        [],
    )

    fingerprint = json.loads(_fingerprint_path(tmp_path, source).read_text())
    assert fingerprint["timestamp"] == 200
    assert fingerprint["proxies"] == []

    state = tracker.get_source_state(source)
    assert state is not None
    assert state[2] == 1
    assert state[3] == pytest.approx(0.0)
    assert state[4:6] == (0, 0)
