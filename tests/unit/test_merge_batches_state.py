# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import os
from pathlib import Path

from scripts.merge_batches import _merge_timeout_history, merge_cache_history


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cache_merge_uses_current_schema_and_newest_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first = tmp_path / "batch_a" / "data" / "test_cache.json"
    second = tmp_path / "batch_b" / "data" / "test_cache.json"
    _write(
        first,
        {
            "same": {
                "tested_at": 100.0,
                "test_count": 5,
                "success_count": 4,
                "is_working": 0,
                "country": "AA",
            }
        },
    )
    _write(
        second,
        {
            "same": {
                "tested_at": 200.0,
                "test_count": 6,
                "success_count": 5,
                "is_working": 1,
                "country": "BB",
            }
        },
    )

    merge_cache_history(str(tmp_path / "batch_*"), str(tmp_path / "output"))
    merged = json.loads(
        (tmp_path / "output/data/test_cache.json").read_text(encoding="utf-8")
    )["same"]
    assert merged["tested_at"] == 200.0
    assert merged["test_count"] == 6
    assert merged["success_count"] == 5
    assert merged["is_working"] == 1
    assert merged["country"] == "BB"
    assert (
        "success" not in merged and "fail" not in merged and "last_seen" not in merged
    )


def test_cache_merge_does_not_multiply_shared_baseline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name, tested_at in (("batch_a", 100.0), ("batch_b", 101.0)):
        _write(
            tmp_path / name / "data/test_cache.json",
            {
                "same": {
                    "tested_at": tested_at,
                    "test_count": 10,
                    "success_count": 8,
                    "is_working": 1,
                }
            },
        )
    merge_cache_history(str(tmp_path / "batch_*"), str(tmp_path / "output"))
    merged = json.loads(
        (tmp_path / "output/data/test_cache.json").read_text(encoding="utf-8")
    )["same"]
    assert merged["test_count"] == 10
    assert merged["success_count"] == 8


def test_timeout_history_ignores_newer_corrupt_candidate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    valid = tmp_path / "batch_a/data/timeout_history.json"
    invalid = tmp_path / "batch_b/data/timeout_history.json"
    _write(valid, {"last_timeout": 12.5})
    invalid.parent.mkdir(parents=True, exist_ok=True)
    invalid.write_text("{broken", encoding="utf-8")
    os.utime(valid, (100, 100))
    os.utime(invalid, (200, 200))

    _merge_timeout_history([tmp_path / "batch_a", tmp_path / "batch_b"])
    payload = json.loads(
        (tmp_path / "data/timeout_history.json").read_text(encoding="utf-8")
    )
    assert payload == {"last_timeout": 12.5}
