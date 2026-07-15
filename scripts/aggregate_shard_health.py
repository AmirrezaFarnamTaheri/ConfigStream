# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reconcile shard lineage and counters into merged metadata."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-glob", default="output_batch_*")
    parser.add_argument("--metadata", type=Path, default=Path("output/metadata.json"))
    parser.add_argument("--expected-shards", type=int, required=True)
    args = parser.parse_args()

    directories = sorted(path for path in Path(".").glob(args.batch_glob) if path.is_dir())
    if len(directories) != args.expected_shards:
        raise SystemExit(
            f"expected {args.expected_shards} shard directories, found {len(directories)}"
        )
    counters: Counter[str] = Counter()
    starts: list[datetime] = []
    ends: list[datetime] = []
    work_seconds = 0.0
    rows = []
    for directory in directories:
        metadata_path = directory / "metadata.json"
        lineage_path = directory / "shard_lineage.json"
        if not metadata_path.is_file() or not lineage_path.is_file():
            raise SystemExit(f"incomplete shard artifact: {directory}")
        metadata = load(metadata_path)
        lineage = load(lineage_path)
        for key in (
            "shielded_count",
            "shielded_candidate_count",
            "shielded_verified_count",
            "warp_attempts",
            "vwarp_attempts",
            "vwarp_success",
        ):
            counters[key] += int(metadata.get(key) or 0)
        duration = float(metadata.get("duration_seconds") or metadata.get("duration") or 0.0)
        work_seconds += duration
        started = parse_time(lineage.get("started_at"))
        completed = parse_time(lineage.get("completed_at"))
        if started:
            starts.append(started)
        if completed:
            ends.append(completed)
        rows.append(
            {
                "batch": lineage.get("batch"),
                "part": lineage.get("part"),
                "source_count": lineage.get("source_count"),
                "source_sha256": lineage.get("source_sha256"),
                "fetched_sources": int(metadata.get("fetched_sources") or 0),
                "tested": int(metadata.get("total_tested") or metadata.get("tested") or 0),
                "working": int(metadata.get("logical_total_working") or metadata.get("working") or 0),
                "time_limited": bool(metadata.get("time_limited")),
                "duration_seconds": duration,
            }
        )
    merged = load(args.metadata)
    for key, value in counters.items():
        merged[key] = value
    wall_seconds = (max(ends) - min(starts)).total_seconds() if starts and ends else 0.0
    merged.update(
        {
            "pipeline_work_seconds_sum": work_seconds,
            "pipeline_wall_clock_seconds": max(0.0, wall_seconds),
            "start_time": min(starts).isoformat() if starts else merged.get("start_time"),
            "end_time": max(ends).isoformat() if ends else merged.get("end_time"),
            "duration": max(0.0, wall_seconds) or merged.get("duration", 0.0),
            "duration_seconds": max(0.0, wall_seconds) or merged.get("duration_seconds", 0.0),
            "shard_summary": {
                "expected": args.expected_shards,
                "observed": len(rows),
                "time_limited": sum(row["time_limited"] for row in rows),
                "zero_source": sum(row["fetched_sources"] == 0 for row in rows),
                "working": sum(row["working"] > 0 for row in rows),
                "shards": rows,
            },
        }
    )
    args.metadata.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(merged["shard_summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
