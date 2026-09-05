# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run-scoped aggregation for source quality and fingerprint evidence."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple, cast

from .config import AppSettings
from .security_validator import SecurityValidator
from .source_quality import SourceQualityTracker

logger = logging.getLogger(__name__)
_SETTINGS_CACHE = AppSettings()

FingerprintKey = Tuple[Any, ...]


@dataclass(frozen=True)
class _ChunkResult:
    fetched: int
    working: int
    duration_ms: float
    geoip_stats: Dict[str, int]
    failure_modes: Dict[str, int]
    fingerprint_keys: frozenset[FingerprintKey]


@dataclass
class _SourceRunAggregate:
    base_failures: int
    base_status: str
    chunks: Dict[int, _ChunkResult] = field(default_factory=dict)


def _normalized_counts(values: Dict[str, int]) -> Dict[str, int]:
    normalized: Dict[str, int] = {}
    for key, value in values.items():
        count = max(0, int(value))
        if count:
            normalized[str(key)] = normalized.get(str(key), 0) + count
    return normalized


def _merge_counts(chunks: Iterable[_ChunkResult], field_name: str) -> Dict[str, int]:
    merged: Dict[str, int] = {}
    for chunk in chunks:
        values = cast(Dict[str, int], getattr(chunk, field_name))
        for key, value in values.items():
            merged[key] = merged.get(key, 0) + value
    return merged


def _diversity_score(country_counts: Dict[str, int]) -> float:
    total = sum(country_counts.values())
    if total <= 0:
        return 0.0
    return 1.0 - sum((count / total) ** 2 for count in country_counts.values())


def _run_key(run_id: str, url: str) -> str:
    raw = f"{run_id}\0{url}".encode("utf-8", errors="surrogatepass")
    return hashlib.sha256(raw).hexdigest()


def _get_aggregate(
    tracker: SourceQualityTracker, run_id: str, url: str
) -> _SourceRunAggregate:
    aggregates = getattr(tracker, "_pipeline_run_aggregates", None)
    if not isinstance(aggregates, dict):
        aggregates = {}
        setattr(tracker, "_pipeline_run_aggregates", aggregates)

    key = (run_id, url)
    aggregate = aggregates.get(key)
    if isinstance(aggregate, _SourceRunAggregate):
        return aggregate

    state = tracker.get_source_state(url)
    base_status = str(state[0]) if state else "active"
    base_failures = int(state[2]) if state and len(state) > 2 else 0
    aggregate = _SourceRunAggregate(
        base_failures=base_failures,
        base_status=base_status,
    )
    aggregates[key] = aggregate
    return aggregate


def _persist_source_state(
    tracker: SourceQualityTracker,
    url: str,
    aggregate: _SourceRunAggregate,
    fetched: int,
    working: int,
    diversity: float,
) -> None:
    reliability = (working / fetched * 100.0) if fetched > 0 else 0.0
    if working > 0:
        failures = 0
        status = "active"
    else:
        failures = aggregate.base_failures + 1
        status = (
            "dead"
            if aggregate.base_status == "dead"
            else tracker._derive_status(failures, None, _SETTINGS_CACHE)
        )

    tracker.upsert_stats(
        url,
        {
            "total_fetched": fetched,
            "total_working": working,
            "consecutive_failures": failures,
            "last_checked": int(datetime.now(timezone.utc).timestamp()),
            "reliability_score": reliability,
            "diversity_score": diversity,
            "trust_score": 50.0,
            "status": status,
        },
    )


def _persist_run_row(
    tracker: SourceQualityTracker,
    url: str,
    run_id: str,
    timestamp: int,
    duration_ms: float,
    fetched: int,
    working: int,
    geoip_stats: Dict[str, int],
    failure_modes: Dict[str, int],
    batch_source: str,
) -> None:
    tracker.execute_write(
        """
        INSERT INTO source_runs(
            run_key, url, timestamp, duration_ms, fetched_count,
            working_count, geoip_json, failure_modes_json, batch_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_key) DO UPDATE SET
            timestamp=excluded.timestamp,
            duration_ms=excluded.duration_ms,
            fetched_count=excluded.fetched_count,
            working_count=excluded.working_count,
            geoip_json=excluded.geoip_json,
            failure_modes_json=excluded.failure_modes_json,
            batch_source=excluded.batch_source
        """,
        (
            _run_key(run_id, url),
            url,
            int(timestamp),
            float(duration_ms),
            int(fetched),
            int(working),
            json.dumps(geoip_stats, sort_keys=True, separators=(",", ":")),
            json.dumps(failure_modes, sort_keys=True, separators=(",", ":")),
            batch_source,
        ),
    )


def _persist_fingerprint(
    url: str,
    run_id: str,
    timestamp: int,
    fingerprint_keys: Iterable[FingerprintKey],
) -> None:
    keys = sorted(
        set(fingerprint_keys),
        key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
    )

    source_hash = hashlib.sha256(url.encode("utf-8", errors="ignore")).hexdigest()
    run_hash = hashlib.sha256(run_id.encode("utf-8", errors="ignore")).hexdigest()[:12]
    fp_dir = Path("data") / "fingerprints"
    fp_dir.mkdir(parents=True, exist_ok=True)
    fp_file = fp_dir / f"{source_hash}.json"
    tmp_file = fp_dir / f".{source_hash}.{run_hash}.tmp"
    payload = {
        "url": SecurityValidator.sanitize_log_message(url),
        "proxies": [list(key) for key in keys],
        "timestamp": int(timestamp),
    }
    tmp_file.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    tmp_file.replace(fp_file)


def record_source_chunk(
    tracker: SourceQualityTracker,
    url: str,
    run_id: str,
    chunk_index: int,
    fetched: int,
    working: int,
    duration_ms: float,
    geoip_stats: Dict[str, int],
    failure_modes: Dict[str, int],
    batch_source: str,
    timestamp: int,
    fingerprint_keys: Iterable[FingerprintKey],
) -> None:
    """Apply one source chunk to a logical run without last-writer-wins loss."""
    logical_run_id = run_id if run_id and run_id != "-" else f"pipeline-{timestamp}"
    chunk_id = max(1, int(chunk_index))
    chunk = _ChunkResult(
        fetched=max(0, int(fetched)),
        working=max(0, int(working)),
        duration_ms=max(0.0, float(duration_ms)),
        geoip_stats=_normalized_counts(geoip_stats),
        failure_modes=_normalized_counts(failure_modes),
        fingerprint_keys=frozenset(fingerprint_keys),
    )

    # QualityStorage already serializes DB access with this RLock. Holding the
    # same lock also makes the in-memory run aggregate and fingerprint replace
    # atomic with respect to other consumer threads for this tracker.
    with tracker._lock:
        aggregate = _get_aggregate(tracker, logical_run_id, url)
        aggregate.chunks[chunk_id] = chunk
        chunks = list(aggregate.chunks.values())
        total_fetched = sum(item.fetched for item in chunks)
        total_working = sum(item.working for item in chunks)
        total_duration_ms = sum(item.duration_ms for item in chunks)
        merged_geoip = _merge_counts(chunks, "geoip_stats")
        merged_failures = _merge_counts(chunks, "failure_modes")
        merged_fingerprints = {
            key for item in chunks for key in item.fingerprint_keys
        }
        diversity = _diversity_score(merged_geoip)

        _persist_source_state(
            tracker,
            url,
            aggregate,
            total_fetched,
            total_working,
            diversity,
        )
        _persist_run_row(
            tracker,
            url,
            logical_run_id,
            timestamp,
            total_duration_ms,
            total_fetched,
            total_working,
            merged_geoip,
            merged_failures,
            batch_source,
        )
        try:
            _persist_fingerprint(
                url,
                logical_run_id,
                timestamp,
                merged_fingerprints,
            )
        except (OSError, TypeError, ValueError) as exc:
            logger.debug(
                "Fingerprint save failed for %s: %s",
                SecurityValidator.sanitize_log_message(url),
                SecurityValidator.sanitize_log_message(str(exc)),
            )
