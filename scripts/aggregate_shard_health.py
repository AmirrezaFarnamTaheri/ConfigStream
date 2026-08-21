# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reconcile shard lineage, source failures, and counters into merged metadata."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

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
LEGACY_FETCH_FAILURE_RE = re.compile(
    r"(?:Failed(?:\s+to\s+fetch)?|Failure)\s*:\s*"
    r"(?P<url>https?://\S+?)\s+-\s+(?P<error>.*?)"
    r"(?:\s+\(Status:\s*(?P<status>\d+)\))?\s*$",
    re.IGNORECASE,
)
FETCH_FAILURE_RE = re.compile(
    r"^Failed\s+to\s+fetch\s+(?P<url>https?://.+?):\s+"
    r"(?P<error>.*?)\s+\(Status:\s*(?P<status>\d+)\)\s*$",
    re.IGNORECASE,
)
FETCH_STATUS_RE = re.compile(r"\(Status:\s*\d+\)\s*$", re.IGNORECASE)
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
LOG_RECORD_START_RE = re.compile(
    r"^\s*(?:\[\d{2}:\d{2}:\d{2}\]\s+)?"
    r"(?:DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+"
)
SOURCE_LOCATION_RE = re.compile(r"\s+[A-Za-z0-9_./-]+\.py:\d+\s*$")


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


def classify_fetch_failure(error: str, status: int = 0) -> str:
    """Map one source acquisition failure to a stable diagnostic category."""

    message = str(error or "").lower()
    if "dns rebinding" in message:
        return "dns_rebinding"
    if any(
        marker in message
        for marker in (
            "could not be resolved",
            "dns resolution",
            "dns validation",
            "resolved to no addresses",
            "name or service not known",
            "nodename nor servname",
        )
    ):
        return "dns_resolution"
    if (
        status in {404, 410}
        or "permanent error: 404" in message
        or "permanent error: 410" in message
    ):
        return "permanent_http"
    if status == 429 or "rate limited" in message:
        return "rate_limited"
    if status >= 500 or re.search(r"\bhttp\s+5\d\d\b", message):
        return "server_error"
    if any(
        marker in message
        for marker in (
            "all connection attempts failed",
            "connecterror",
            "connection refused",
            "connection reset",
            "server disconnected",
            "network is unreachable",
        )
    ):
        return "connect_error"
    if "timed out" in message or "timeout" in message:
        return "timeout"
    if "circuit breaker open" in message:
        return "circuit_breaker"
    return "other"


def _rich_failure_records(text: str) -> Iterator[str]:
    """Reassemble Rich-wrapped producer warnings into logical failure records."""

    current: str | None = None
    for raw_line in text.splitlines():
        line = ANSI_ESCAPE_RE.sub("", raw_line)
        line = SOURCE_LOCATION_RE.sub("", line).rstrip()
        record_start = LOG_RECORD_START_RE.match(line)
        fragment = (line[record_start.end() :] if record_start else line).strip()

        if record_start:
            current = None
            offset = fragment.lower().find("failed to fetch")
            if offset >= 0:
                current = fragment[offset:]
        elif current is not None and fragment:
            current = f"{current} {fragment}"

        if current is not None and FETCH_STATUS_RE.search(current):
            yield current
            current = None


def _source_host(raw_url: str) -> str:
    """Extract a host even when console wrapping split a URL token."""

    normalized = re.sub(r"\s+", "", raw_url)
    try:
        host = urlparse(normalized).hostname
    except ValueError:
        host = None
    if not host:
        fallback = re.match(r"https?://([^/:]+)", normalized, re.IGNORECASE)
        host = fallback.group(1) if fallback else "unknown"
    return host.rstrip(".").lower()


def _record_failure(
    match: re.Match[str],
    categories: Counter[str],
    hosts: Counter[str],
    host_categories: Counter[str],
) -> None:
    raw_url = match.group("url")
    error = match.group("error") or ""
    status = int(match.group("status") or 0)
    host = _source_host(raw_url)
    category = classify_fetch_failure(error, status)
    categories[category] += 1
    hosts[host] += 1
    host_categories[f"{host}:{category}"] += 1


def fetch_failure_counts(log_path: Path) -> dict[str, Any]:
    """Return privacy-safe failure counts by category and logical source host."""

    categories: Counter[str] = Counter()
    hosts: Counter[str] = Counter()
    host_categories: Counter[str] = Counter()
    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        text = ""

    for line in text.splitlines():
        match = LEGACY_FETCH_FAILURE_RE.search(line)
        if match:
            _record_failure(match, categories, hosts, host_categories)

    for record in _rich_failure_records(text):
        match = FETCH_FAILURE_RE.match(record)
        if match:
            _record_failure(match, categories, hosts, host_categories)

    return {
        "total": sum(categories.values()),
        "by_category": dict(categories.most_common()),
        "by_host": dict(hosts.most_common()),
        "by_host_category": dict(host_categories.most_common()),
    }


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
    failure_categories: Counter[str] = Counter()
    failure_hosts: Counter[str] = Counter()
    failure_host_categories: Counter[str] = Counter()
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
        shard_failures = fetch_failure_counts(fetch_log)
        failure_categories.update(shard_failures["by_category"])
        failure_hosts.update(shard_failures["by_host"])
        failure_host_categories.update(shard_failures["by_host_category"])
        rows.append(
            {
                "batch": lineage.get("batch"),
                "part": lineage.get("part"),
                "source_count": source_count,
                "source_sha256": lineage.get("source_sha256"),
                "fetched_sources": covered_sources,
                "source_attempts": source_attempts,
                "source_failures": shard_failures,
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
    source_failure_summary = {
        "total": sum(failure_categories.values()),
        "by_category": dict(failure_categories.most_common()),
        "by_host": dict(failure_hosts.most_common()),
        "by_host_category": dict(failure_host_categories.most_common()),
    }
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
            "source_failure_summary": source_failure_summary,
            "shard_summary": {
                "expected": expected,
                "observed": len(rows),
                "time_limited": sum(bool(row["time_limited"]) for row in rows),
                "zero_source": sum(int(row["fetched_sources"]) == 0 for row in rows),
                "working": sum(int(row["working"]) > 0 for row in rows),
                "source_attempts": source_attempts,
                "covered_sources": covered_sources,
                "configured_sources": configured_sources,
                "source_failures": source_failure_summary,
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
