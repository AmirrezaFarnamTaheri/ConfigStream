# SPDX-License-Identifier: AGPL-3.0-or-later
"""Normalize Rich-wrapped source timing logs into stable machine-readable evidence."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, cast

from configstream.security_validator import SecurityValidator

try:
    from shard_sources import partition
except ModuleNotFoundError:
    from scripts.shard_sources import partition

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SUMMARY_START_RE = re.compile(r"Source\s+Summary\b[^\[]*\[", re.IGNORECASE)
SUMMARY_HEAD_RE = re.compile(
    r"Source\s+Summary\b[^\[]*\[(?P<url>.*?)\]\s*:\s*(?P<body>.*)",
    re.IGNORECASE | re.DOTALL,
)
RAW_RE = re.compile(r"\bRaw\s*=\s*(\d+)", re.IGNORECASE)
FETCH_RE = re.compile(r"\bFetch\s*[:=]\s*([\d.]+)\s*ms", re.IGNORECASE)
DURATION_RE = re.compile(r"\bDur\s*=\s*([\d.]+)\s*ms", re.IGNORECASE)
SHARD_LOG_RE = re.compile(
    r"^pipeline_batch_(?P<batch>.+?)_part_(?P<part>\d+)\.log$",
    re.IGNORECASE,
)
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


def _normalize_logged_url(value: str) -> str:
    """Undo whitespace inserted by Rich line wrapping inside logged URLs."""

    return re.sub(r"\s+", "", value.strip())


def _source_key(url: str) -> str:
    cleaned = _normalize_logged_url(url).replace("[MASKED]", "").replace("[BASE64]", "")
    cleaned = cleaned.split("#", 1)[0].split("?", 1)[0]
    return cleaned.rstrip()


def _sanitized_source_key(url: str) -> str:
    return _normalize_logged_url(SecurityValidator.sanitize_log_message(url))


def parse_source_timings(text: str, source_log: str = "") -> list[SourceTiming]:
    """Parse source summaries even when Rich wraps or annotates logical records."""

    flattened = _flatten(text)
    starts = list(SUMMARY_START_RE.finditer(flattened))
    records: list[SourceTiming] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(flattened)
        segment = flattened[start.start() : end]
        match = SUMMARY_HEAD_RE.match(segment)
        if match is None:
            continue
        url = _normalize_logged_url(match.group("url"))
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


def collect_raw_timings(log_files: Iterable[Path]) -> list[SourceTiming]:
    records: list[SourceTiming] = []
    for path in log_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        records.extend(parse_source_timings(text, path.name))
    return records


def collect_timings(log_files: Iterable[Path]) -> list[SourceTiming]:
    """Collect one conservative record per logged URL, keeping the slowest."""

    by_url: dict[str, SourceTiming] = {}
    for record in collect_raw_timings(log_files):
        key = _source_key(record.url)
        if not key:
            continue
        previous = by_url.get(key)
        if previous is None or record.duration_ms > previous.duration_ms:
            by_url[key] = record
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


def load_expected_sources_by_batch(pattern: str) -> dict[str, list[str]]:
    batches: dict[str, list[str]] = {}
    for item in sorted(glob.glob(pattern)):
        path = Path(item)
        batch = path.stem.removeprefix("batch_")
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.strip()
            and not line.lstrip().startswith("#")
            and line.strip().startswith(("http://", "https://"))
        ]
        batches[batch] = lines
    return batches


def infer_shard_parts(
    log_files: Iterable[Path],
    configured_parts: int | None = None,
    *,
    lineage_files: Iterable[Path] = (),
) -> int:
    """Return the authoritative runtime shard count and validate observed logs."""

    if configured_parts is None:
        lineage_parts: list[int] = []
        for path in lineage_files:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                part = int(payload.get("part") or 0) if isinstance(payload, dict) else 0
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue
            if part > 0:
                lineage_parts.append(part)
        if not lineage_parts:
            raise ValueError("runtime shard count requires --parts or shard lineage")
        configured_parts = max(lineage_parts)

    if configured_parts <= 0:
        raise ValueError("runtime shard count must be positive")

    observed_parts = [
        int(match.group("part"))
        for path in log_files
        if (match := SHARD_LOG_RE.match(path.name)) is not None
    ]
    if any(part <= 0 or part > configured_parts for part in observed_parts):
        raise ValueError("observed shard part is outside the configured shard count")
    return configured_parts


def _candidate_sources_for_log(
    source_log: str,
    sources_by_batch: dict[str, list[str]],
    parts: int,
) -> list[str]:
    if parts <= 0:
        raise ValueError("runtime shard count must be positive")
    match = SHARD_LOG_RE.match(Path(source_log).name)
    if match is None:
        return []
    batch_sources = sources_by_batch.get(match.group("batch"), [])
    part = int(match.group("part"))
    buckets = (
        cast(list[list[str]], partition(batch_sources, parts)) if batch_sources else []
    )
    if part < 1 or part > len(buckets):
        return []
    return buckets[part - 1]


def _canonical_matches(
    record: SourceTiming,
    sources_by_batch: dict[str, list[str]],
    parts: int,
) -> list[str]:
    candidates = _candidate_sources_for_log(record.source_log, sources_by_batch, parts)
    observed = _normalize_logged_url(record.url)
    matches = [url for url in candidates if _sanitized_source_key(url) == observed]
    if not matches:
        matches = [url for url in candidates if _normalize_logged_url(url) == observed]
    if not matches:
        observed_key = _source_key(observed)
        matches = [url for url in candidates if _source_key(url) == observed_key]
    return matches if len(matches) == 1 else []


def _timing_identity(record: SourceTiming) -> tuple[str, str]:
    return record.source_log, _normalize_logged_url(record.url)


def timing_resolution_counts(
    records: Iterable[SourceTiming],
    sources_by_batch: dict[str, list[str]],
    parts: int,
) -> tuple[int, int]:
    """Return mapped and observed logical timing identities.

    Multiple chunks from the same source can emit repeated summaries. Count each
    sanitized source identity once per deterministic shard, and only count it as
    mapped when exactly one canonical source in that shard produces the logged
    sanitized URL. Ambiguous sanitizer collisions remain unresolved rather than
    fabricating timing evidence for multiple sources.
    """

    identities: dict[tuple[str, str], SourceTiming] = {}
    for record in records:
        identities.setdefault(_timing_identity(record), record)
    mapped = sum(
        bool(_canonical_matches(record, sources_by_batch, parts))
        for record in identities.values()
    )
    return mapped, len(identities)


def resolve_timings(
    records: Iterable[SourceTiming],
    sources_by_batch: dict[str, list[str]],
    parts: int,
) -> list[SourceTiming]:
    """Resolve unambiguous sanitized log URLs to canonical shard sources."""

    by_url: dict[str, SourceTiming] = {}
    for record in records:
        matches = _canonical_matches(record, sources_by_batch, parts)
        if not matches:
            continue
        canonical_url = matches[0]
        resolved = replace(record, url=canonical_url)
        previous = by_url.get(canonical_url)
        if previous is None or resolved.duration_ms > previous.duration_ms:
            by_url[canonical_url] = resolved
    return [by_url[url] for url in sorted(by_url)]


def timing_coverage(
    records: Iterable[SourceTiming], expected_sources: Iterable[str]
) -> float:
    expected_keys = {_source_key(url) for url in expected_sources if _source_key(url)}
    if not expected_keys:
        return 0.0
    observed_keys = {
        _source_key(record.url) for record in records if _source_key(record.url)
    }
    return len(expected_keys & observed_keys) / len(expected_keys)


def source_id_for_url(url: str) -> str:
    return hashlib.sha256(_normalize_logged_url(url).encode("utf-8")).hexdigest()


def write_outputs(
    records: list[SourceTiming], normalized_log: Path, evidence_jsonl: Path
) -> None:
    normalized_log.parent.mkdir(parents=True, exist_ok=True)
    evidence_jsonl.parent.mkdir(parents=True, exist_ok=True)
    normalized_lines: list[str] = []
    evidence_lines: list[str] = []
    for record in records:
        safe_url = SecurityValidator.sanitize_log_message(record.url)
        safe_source_log = SecurityValidator.sanitize_log_message(record.source_log)
        fetch = f" Fetch={record.fetch_ms:g}ms" if record.fetch_ms is not None else ""
        normalized_lines.append(
            f"Source Summary [{safe_url}]: Raw={record.raw}{fetch} "
            f"Dur={record.duration_ms:g}ms"
        )
        evidence_lines.append(
            json.dumps(
                {
                    "source_id": source_id_for_url(record.url),
                    "source_url": safe_url,
                    "raw": record.raw,
                    "fetch_ms": record.fetch_ms,
                    "duration_ms": record.duration_ms,
                    "source_log": safe_source_log,
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


def _clear_outputs(*paths: Path) -> bool:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            safe_path = SecurityValidator.sanitize_log_message(str(path))
            print(
                "ERROR: could not clear stale timing output "
                f"{safe_path}: {type(exc).__name__}",
                file=sys.stderr,
            )
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pattern", default="pipeline_batch_*.log", help="Shard log glob pattern"
    )
    parser.add_argument(
        "--sources-pattern",
        default="sources/batch_*.txt",
        help="Canonical source-file glob used to resolve timing evidence",
    )
    parser.add_argument(
        "--lineage-pattern",
        default="output_batch_*/shard_lineage.json",
        help="Shard-lineage glob used when --parts is not supplied",
    )
    parser.add_argument(
        "--parts",
        type=int,
        help="Authoritative runtime shard count; otherwise derived from lineage",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=DEFAULT_MIN_COVERAGE,
        help="Minimum fraction of logged timing identities requiring canonical mapping",
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

    if not _clear_outputs(args.normalized_log, args.evidence):
        return 1

    log_files = [Path(item) for item in sorted(glob.glob(args.pattern))]
    if not log_files:
        print(
            "ERROR: no shard logs available for timing normalization", file=sys.stderr
        )
        return 1

    raw_records = collect_raw_timings(log_files)
    if not raw_records:
        print(
            "ERROR: shard logs contained no parseable Source Summary timing records",
            file=sys.stderr,
        )
        return 1

    sources_by_batch = load_expected_sources_by_batch(args.sources_pattern)
    expected_sources = {url for urls in sources_by_batch.values() for url in urls}
    if not expected_sources:
        print(
            "ERROR: no canonical sources available for timing coverage", file=sys.stderr
        )
        return 1

    lineage_files = [Path(item) for item in sorted(glob.glob(args.lineage_pattern))]
    try:
        parts = infer_shard_parts(
            log_files,
            args.parts,
            lineage_files=lineage_files,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    mapped, observed = timing_resolution_counts(raw_records, sources_by_batch, parts)
    coverage = mapped / observed if observed else 0.0
    min_coverage = max(0.0, min(float(args.min_coverage), 1.0))
    print(
        f"INFO: source timing identity coverage {coverage:.1%} "
        f"({mapped} mapped, {observed} observed identities, "
        f"{len(expected_sources)} configured sources)"
    )
    if coverage < min_coverage:
        print(
            f"ERROR: source timing identity coverage {coverage:.1%} is below "
            f"the required {min_coverage:.1%}",
            file=sys.stderr,
        )
        return 1

    records = resolve_timings(raw_records, sources_by_batch, parts)
    if not records:
        print(
            "ERROR: source timing records could not be mapped to canonical shard "
            "sources",
            file=sys.stderr,
        )
        return 1

    write_outputs(records, args.normalized_log, args.evidence)
    print(
        f"OK: normalized {len(records)} canonical source timing records from "
        f"{len(log_files)} shard log(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
