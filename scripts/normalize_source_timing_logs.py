# SPDX-License-Identifier: AGPL-3.0-or-later
"""Normalize Rich-wrapped source timing logs into stable machine-readable evidence."""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SUMMARY_START_RE = re.compile(r"Source\s+Summary\s+\[", re.IGNORECASE)
SUMMARY_HEAD_RE = re.compile(
    r"Source\s+Summary\s+\[(?P<url>.*?)\]\s*:\s*(?P<body>.*)",
    re.IGNORECASE | re.DOTALL,
)
RAW_RE = re.compile(r"\bRaw\s*=\s*(\d+)", re.IGNORECASE)
FETCH_RE = re.compile(r"\bFetch\s*[:=]\s*([\d.]+)\s*ms", re.IGNORECASE)
DURATION_RE = re.compile(r"\bDur\s*=\s*([\d.]+)\s*ms", re.IGNORECASE)
DEFAULT_MIN_COVERAGE = 0.80


@dataclass(frozen=True)
class SourceTiming:
    url: str
    raw: int
    duration_ms: float
    fetch_ms: float | None
    source_log: str


def _flatten(text: str) -> str:
    return re.sub(r"\s+", " ", ANSI_RE.sub("", text)).strip()


def _source_key(url: str) -> str:
    cleaned = url.strip().replace("[MASKED]", "").replace("[BASE64]", "")
    cleaned = cleaned.split("#", 1)[0].split("?", 1)[0]
    return cleaned.rstrip()


def parse_source_timings(text: str, source_log: str = "") -> list[SourceTiming]:
    """Parse source summaries even when Rich wraps one logical record across lines."""

    flattened = _flatten(text)
    starts = list(SUMMARY_START_RE.finditer(flattened))
    records: list[SourceTiming] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(flattened)
        segment = flattened[start.start() : end]
        match = SUMMARY_HEAD_RE.match(segment)
        if match is None:
            continue
        url = match.group("url").strip()
        body = match.group("body")
        raw_match = RAW_RE.search(body)
        duration_match = DURATION_RE.search(body)
        if not url or duration_match is None:
            continue
        fetch_match = FETCH_RE.search(body)
        records.append(
            SourceTiming(
                url=url,
                raw=int(raw_match.group(1)) if raw_match else 0,
                duration_ms=float(duration_match.group(1)),
                fetch_ms=float(fetch_match.group(1)) if fetch_match else None,
                source_log=source_log,
            )
        )
    return records


def collect_timings(log_files: Iterable[Path]) -> list[SourceTiming]:
    """Collect one conservative record per source URL, keeping the slowest duration."""

    by_url: dict[str, SourceTiming] = {}
    for path in log_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for record in parse_source_timings(text, path.name):
            previous = by_url.get(record.url)
            if previous is None or record.duration_ms > previous.duration_ms:
                by_url[record.url] = record
    return [by_url[url] for url in sorted(by_url)]


def load_expected_sources(pattern: str) -> set[str]:
    sources: set[str] = set()
    for item in sorted(glob.glob(pattern)):
        path = Path(item)
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            if value.startswith(("http://", "https://")):
                sources.add(value)
    return sources


def timing_coverage(records: Iterable[SourceTiming], expected_sources: Iterable[str]) -> float:
    expected_keys = {_source_key(url) for url in expected_sources if _source_key(url)}
    if not expected_keys:
        return 0.0
    observed_keys = {_source_key(record.url) for record in records if _source_key(record.url)}
    return len(expected_keys & observed_keys) / len(expected_keys)


def write_outputs(
    records: list[SourceTiming], normalized_log: Path, evidence_jsonl: Path
) -> None:
    normalized_log.parent.mkdir(parents=True, exist_ok=True)
    evidence_jsonl.parent.mkdir(parents=True, exist_ok=True)
    normalized_lines: list[str] = []
    evidence_lines: list[str] = []
    for record in records:
        fetch = f" Fetch={record.fetch_ms:g}ms" if record.fetch_ms is not None else ""
        normalized_lines.append(
            f"Source Summary [{record.url}]: Raw={record.raw}{fetch} "
            f"Dur={record.duration_ms:g}ms"
        )
        evidence_lines.append(
            json.dumps(
                {
                    "source_url": record.url,
                    "raw": record.raw,
                    "fetch_ms": record.fetch_ms,
                    "duration_ms": record.duration_ms,
                    "source_log": record.source_log,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    normalized_log.write_text(
        "\n".join(normalized_lines) + ("\n" if normalized_lines else ""),
        encoding="utf-8",
    )
    evidence_jsonl.write_text(
        "\n".join(evidence_lines) + ("\n" if evidence_lines else ""),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pattern", default="pipeline_batch_*.log", help="Shard log glob pattern"
    )
    parser.add_argument(
        "--sources-pattern",
        default="sources/batch_*.txt",
        help="Canonical source-file glob used to calculate timing coverage",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=DEFAULT_MIN_COVERAGE,
        help="Minimum fraction of canonical sources requiring real timing evidence",
    )
    parser.add_argument(
        "--normalized-log",
        type=Path,
        default=Path("source_timing_normalized.log"),
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("pipeline-evidence/source_timing.jsonl"),
    )
    args = parser.parse_args()

    log_files = [Path(item) for item in sorted(glob.glob(args.pattern))]
    if not log_files:
        print("ERROR: no shard logs available for timing normalization", file=sys.stderr)
        return 1

    records = collect_timings(log_files)
    write_outputs(records, args.normalized_log, args.evidence)
    if not records:
        print(
            "ERROR: shard logs contained no parseable Source Summary timing records",
            file=sys.stderr,
        )
        return 1

    expected_sources = load_expected_sources(args.sources_pattern)
    if not expected_sources:
        print("ERROR: no canonical sources available for timing coverage", file=sys.stderr)
        return 1
    coverage = timing_coverage(records, expected_sources)
    min_coverage = max(0.0, min(float(args.min_coverage), 1.0))
    print(
        f"INFO: source timing coverage {coverage:.1%} "
        f"({len(records)} records, {len(expected_sources)} canonical sources)"
    )
    if coverage < min_coverage:
        print(
            f"ERROR: source timing coverage {coverage:.1%} is below "
            f"the required {min_coverage:.1%}",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK: normalized {len(records)} source timing records from {len(log_files)} shard log(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
