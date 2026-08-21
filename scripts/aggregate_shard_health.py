# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reconcile shard lineage and counters into merged metadata."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from shard_sources import partition
except ModuleNotFoundError:
    from scripts.shard_sources import partition

REPO_ROOT = Path(__file__).resolve().parents[1]
FETCH_SUMMARY_RE = re.compile(
    r"Fetch\s+Summary:\s*"
    r"(?P<successful>\d+)\s*/\s*(?P<attempted>\d+)\s+"
    r"sources\s+successful",
    re.IGNORECASE,
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def expected_from_sources(sources_dir: Path, parts: int) -> int:
    expected = 0
    for source_file in sorted(sources_dir.glob("batch_*.txt")):
        lines = [
            line.strip()
            for line in source_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        expected += sum(bool(bucket) for bucket in partition(lines, parts))
    return expected


def bounded_source_counts(source_count: int, fetched_sources: int) -> tuple[int, int]:
    """Return processable-source estimate and raw consumer queue observations."""

    assigned = max(0, int(source_count or 0))
    observations = max(0, int(fetched_sources or 0))
    processable = min(assigned, observations) if assigned else 0
    return processable, observations


def fetch_summary_counts(
    log_path: Path,
    *,
    source_count: int,
    fallback_fetched_sources: int,
) -> tuple[int, int]:
    """Return unique successful source fetches and source attempts.

    Shard ``metadata.fetched_sources`` is updated by consumers for every queued
    chunk, so it is not a unique source count. The producer's Fetch Summary is
    emitted once per fetch batch and carries the actual source success / attempt
    counts. Fall back to the old bounded estimate only when a shard log is absent.
    """

    fallback_covered, fallback_attempts = bounded_source_counts(
        source_count, fallback_fetched_sources
    )
    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return fallback_covered, fallback_attempts

    matches = list(FETCH_SUMMARY_RE.finditer(text))
    if not matches:
        return fallback_covered, fallback_attempts

    successful = sum(int(match.group("successful")) for match in matches)
    attempted = sum(int(match.group("attempted")) for match in matches)
    assigned = max(0, int(source_count or 0))
    if assigned:
        successful = min(successful, assigned)
        attempted = min(attempted, assigned)
    successful = min(successful, attempted)
    return successful, attempted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-glob", default="output_batch_*")
    parser.add_argument("--metadata", type=Path, default=Path("output/metadata.json"))
    parser.add_argument("--expected-shards", type=int)
    parser.add_argument("--sources-dir", type=Path, default=Path("sources"))
    parser.add_argument("--parts", type=int, default=4)
    parser.add_argument("--log-dir", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    log_root = args.log_dir.resolve()

    expected = args.expected_shards or expected_from_sources(
        args.sources_dir, args.parts
    )
    if expected <= 0:
        raise SystemExit("could not derive expected shard count")
    directories = sorted(
        path for path in Path(".").glob(args.batch_glob) if path.is_dir()
    )
    if len(directories) != expected:
        raise SystemExit(
            f"expected {expected} shard directories, found {len(directories)}"
        )
    counters: Counter[str] = Counter()
    starts: list[datetime] = []
    ends: list[datetime] = []
    work_seconds = 0.0
    rows: list[dict[str, Any]] = []
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
        duration = float(
            metadata.get("duration_seconds") or metadata.get("duration") or 0.0
        )
        work_seconds += duration
        started = parse_time(lineage.get("started_at"))
        completed = parse_time(lineage.get("completed_at"))
        if started:
            starts.append(started)
        if completed:
            ends.append(completed)
        batch = str(lineage.get("batch") or "").strip()
        part = int(lineage.get("part") or 0)
        source_count = int(lineage.get("source_count") or 0)
        fetch_log = log_root / f"pipeline_batch_{batch}_part_{part}.log"
        covered_sources, source_attempts = fetch_summary_counts(
            fetch_log,
            source_count=source_count,
            fallback_fetched_sources=int(metadata.get("fetched_sources") or 0),
        )
        rows.append(
            {
                "batch": lineage.get("batch"),
                "part": lineage.get("part"),
                "source_count": source_count,
                "source_sha256": lineage.get("source_sha256"),
                "fetched_sources": covered_sources,
                "source_attempts": source_attempts,
                "tested": int(
                    metadata.get("total_tested") or metadata.get("tested") or 0
                ),
                "working": int(
                    metadata.get("logical_total_working")
                    or metadata.get("working")
                    or 0
                ),
                "time_limited": bool(metadata.get("time_limited")),
                "duration_seconds": duration,
            }
        )
    merged = load(args.metadata)
    for key, value in counters.items():
        merged[key] = value
    wall_seconds = (max(ends) - min(starts)).total_seconds() if starts and ends else 0.0
    configured_sources = sum(int(row["source_count"]) for row in rows)
    covered_sources = sum(int(row["fetched_sources"]) for row in rows)
    source_attempts = sum(int(row["source_attempts"]) for row in rows)
    merged.update(
        {
            "pipeline_work_seconds_sum": work_seconds,
            "pipeline_wall_clock_seconds": max(0.0, wall_seconds),
            "start_time": (
                min(starts).isoformat() if starts else merged.get("start_time")
            ),
            "end_time": max(ends).isoformat() if ends else merged.get("end_time"),
            "duration": max(0.0, wall_seconds) or merged.get("duration", 0.0),
            "duration_seconds": max(0.0, wall_seconds)
            or merged.get("duration_seconds", 0.0),
            "fetched_sources": covered_sources,
            "total_configured_sources": configured_sources,
            "shard_summary": {
                "expected": expected,
                "observed": len(rows),
                "time_limited": sum(bool(row["time_limited"]) for row in rows),
                "zero_source": sum(int(row["fetched_sources"]) == 0 for row in rows),
                "working": sum(int(row["working"]) > 0 for row in rows),
                "source_attempts": source_attempts,
                "covered_sources": covered_sources,
                "configured_sources": configured_sources,
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
