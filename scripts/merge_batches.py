# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import asyncio
import glob
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from datetime import datetime, timezone

from configstream.anomaly import AnomalyDetector
from configstream.config import AppSettings
from configstream.filtering import dedupe_and_shuffle, filter_unique_endpoints
from configstream.history.tracker import ProxyHistoryTracker
from configstream.models import Proxy
from configstream.pipeline_core import output_handler
from configstream.pipeline_core.sorter import sort_proxies_pareto
from configstream.pipeline_core.stats import PipelineStats
from configstream.quality.storage import QualityStorage

logger = logging.getLogger(__name__)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on")
    return False


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to read JSON {path}: {e}")
        return None


def _proxy_from_dict(raw: Dict[str, Any]) -> Optional[Proxy]:
    config = str(raw.get("config") or "").strip()
    protocol = str(raw.get("protocol") or "").strip()
    address = str(raw.get("address") or "").strip()
    port_raw = raw.get("port")
    if not config or not protocol or not address:
        return None
    port = _coerce_int(port_raw)
    if port is None:
        return None
    if port <= 0 or port > 65535:
        return None

    details = raw.get("details")
    if not isinstance(details, dict):
        details = {}

    tags = raw.get("tags")
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list):
        tags = []

    security = raw.get("security")
    if not isinstance(security, dict):
        security = {}

    latency = _coerce_float(raw.get("latency"))
    is_working = _coerce_bool(raw.get("is_working", True))

    country_code = str(raw.get("country_code") or raw.get("country") or "")
    return Proxy(
        config=config,
        protocol=protocol,
        address=address,
        port=port,
        uuid=str(raw.get("uuid") or ""),
        remarks=str(raw.get("remarks") or ""),
        country=str(raw.get("country") or country_code),
        country_code=country_code,
        city=str(raw.get("city") or ""),
        asn=str(raw.get("asn") or ""),
        isp=str(raw.get("isp") or ""),
        org=str(raw.get("org") or ""),
        latency=latency,
        is_working=is_working,
        tags=tags,
        security_issues=security,
        tested_at=str(raw.get("tested_at") or raw.get("last_checked") or ""),
        details=details,
        process=str(raw.get("process") or "native"),
    )


def _load_proxies_from_file(path: Path) -> List[Proxy]:
    data = _load_json(path)
    if not isinstance(data, list):
        print(f"Skipped {path}: expected JSON list")
        return []

    proxies: List[Proxy] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            proxy = _proxy_from_dict(item)
            if proxy:
                proxies.append(proxy)
        except Exception:
            continue
    return proxies


def _find_batch_dirs(batch_glob: str) -> List[Path]:
    return sorted(
        [Path(p) for p in glob.glob(batch_glob) if Path(p).is_dir()],
        key=lambda p: p.name,
    )


def merge_cache_history(batch_glob: str, output_dir: str) -> None:
    print("--- Merging Cache History ---")
    merged_cache = {}

    # Look for cache files in batch directories
    pattern = os.path.join(batch_glob, "data", "test_cache.json")
    files = glob.glob(pattern)

    # Also look in root of batch just in case
    files.extend(glob.glob(os.path.join(batch_glob, "test_cache.json")))

    # Fall back to any root-level cache artifacts that may have been downloaded
    files.extend(glob.glob(os.path.join("data", "test_cache.json")))

    files = sorted(list(set(files)))

    print(f"Found {len(files)} cache files.")

    for fpath in files:
        try:
            with open(fpath, "r") as f:
                data = json.load(f)
                # Smart Aggregation instead of .update()
                for phash, stats in data.items():
                    if not isinstance(stats, dict):
                        continue

                    if phash not in merged_cache:
                        item = dict(stats)
                        hist = item.get("history")
                        if not isinstance(hist, list):
                            item.pop("history", None)
                        merged_cache[phash] = item
                    else:
                        # Aggregate stats
                        existing = merged_cache[phash]
                        existing["success"] = existing.get("success", 0) + stats.get(
                            "success", 0
                        )
                        existing["fail"] = existing.get("fail", 0) + stats.get(
                            "fail", 0
                        )

                        # Max last_seen
                        existing["last_seen"] = max(
                            existing.get("last_seen", 0), stats.get("last_seen", 0)
                        )

                        # History list append (only if well-formed)
                        incoming_hist = stats.get("history")
                        if isinstance(incoming_hist, list):
                            existing_hist = existing.get("history")
                            if not isinstance(existing_hist, list):
                                existing_hist = []
                            existing_hist.extend(incoming_hist)
                            existing["history"] = sorted(
                                existing_hist,
                                key=lambda x: (
                                    x.get("timestamp", 0) if isinstance(x, dict) else 0
                                ),
                            )[-20:]

                # print(f"Merged {len(data)} entries from {fpath}")
        except Exception as e:
            print(f"Failed to merge {fpath}: {e}")

    # Write merged file
    os.makedirs(os.path.join(output_dir, "data"), exist_ok=True)
    out_path = os.path.join(output_dir, "data", "test_cache.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged_cache, f)
    print(f"Total merged entries: {len(merged_cache)}")


def _merge_quality_db(batch_dirs: Iterable[Path]) -> None:
    target = Path("data") / "source_quality.db"
    target.parent.mkdir(parents=True, exist_ok=True)
    storage = QualityStorage(target)
    merged = 0
    for batch_dir in batch_dirs:
        candidate = batch_dir / "data" / "source_quality.db"
        if candidate.exists():
            storage.merge_from(candidate)
            merged += 1
    print(f"Merged source_quality.db from {merged} batch(es).")


def _merge_anomaly_db(batch_dirs: Iterable[Path]) -> None:
    target = Path("data") / "anomaly.db"
    target.parent.mkdir(parents=True, exist_ok=True)
    detector = AnomalyDetector(target)
    merged = 0
    for batch_dir in batch_dirs:
        candidate = batch_dir / "data" / "anomaly.db"
        if candidate.exists():
            detector.merge_from(candidate)
            merged += 1
    print(f"Merged anomaly.db from {merged} batch(es).")


def _merge_history_db(batch_dirs: Iterable[Path]) -> ProxyHistoryTracker:
    history_path = Path("data") / "history.db"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    tracker = ProxyHistoryTracker(history_path)
    merged = 0
    for batch_dir in batch_dirs:
        candidate = batch_dir / "data" / "history.db"
        if candidate.exists():
            tracker.storage.merge_from(candidate)
            merged += 1
    print(f"Merged history.db from {merged} batch(es).")
    return tracker


def _merge_timeout_history(batch_dirs: Iterable[Path]) -> None:
    candidates = []
    for batch_dir in batch_dirs:
        candidate = batch_dir / "data" / "timeout_history.json"
        if candidate.exists():
            candidates.append(candidate)
    if not candidates:
        return

    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    target = Path("data") / "timeout_history.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(latest.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Updated timeout_history.json from {latest}.")


def _merge_metadata(batch_dirs: Iterable[Path]) -> Dict[str, Any]:
    totals: Dict[str, Any] = {
        "fetched_lines": 0,
        "parsed": 0,
        "tested": 0,
        "geo_resolved": 0,
        "cache_misses": 0,
        "duration": 0.0,
        "fetched_sources": 0,
        "total_configured_sources": 0,
        "vwarp_attempts": 0,
        "vwarp_success": 0,
        "revived_warp": 0,
        "revived_vwarp": 0,
        "time_limited": False,
        "time_limit_seconds": 0,
    }
    drop_reasons: Dict[str, int] = {}

    for batch_dir in batch_dirs:
        meta_path = batch_dir / "metadata.json"
        if not meta_path.exists():
            continue
        data = _load_json(meta_path)
        if not isinstance(data, dict):
            continue

        totals["fetched_lines"] += int(
            data.get("total_lines_sourced", data.get("fetched_lines", 0)) or 0
        )
        totals["parsed"] += int(
            data.get("total_unique_candidates", data.get("parsed", 0)) or 0
        )
        totals["tested"] += int(data.get("total_tested", data.get("tested", 0)) or 0)
        totals["geo_resolved"] += int(data.get("geo_resolved", 0) or 0)
        totals["cache_misses"] += int(data.get("cache_misses", 0) or 0)
        totals["duration"] += float(data.get("duration_seconds", 0.0) or 0.0)
        totals["fetched_sources"] += int(data.get("fetched_sources", 0) or 0)
        totals["total_configured_sources"] += int(
            data.get("sources_count", data.get("total_sources", 0)) or 0
        )
        totals["vwarp_attempts"] += int(data.get("vwarp_attempts", 0) or 0)
        totals["vwarp_success"] += int(data.get("vwarp_success", 0) or 0)
        totals["revived_warp"] += int(data.get("revived_warp", 0) or 0)
        totals["revived_vwarp"] += int(data.get("revived_vwarp", 0) or 0)

        if data.get("time_limited"):
            totals["time_limited"] = True
        try:
            limit_val = int(data.get("time_limit_seconds", 0) or 0)
            if limit_val > totals["time_limit_seconds"]:
                totals["time_limit_seconds"] = limit_val
        except (TypeError, ValueError):
            pass

        reasons = data.get("rejection_reasons", data.get("drop_reasons", {}))
        if isinstance(reasons, dict):
            for key, val in reasons.items():
                try:
                    drop_reasons[key] = drop_reasons.get(key, 0) + int(val)
                except (TypeError, ValueError):
                    continue

    totals["drop_reasons"] = drop_reasons
    return totals


def _merge_logs(output_dir: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    log_files = sorted(Path(".").glob("pipeline_batch_*.log"))
    if not log_files:
        return
    consolidated = output_path / "consolidated_pipeline.log"
    with consolidated.open("w", encoding="utf-8") as out_f:
        for log_path in log_files:
            out_f.write(f"===== {log_path.name} =====\n")
            out_f.write(log_path.read_text(encoding="utf-8", errors="ignore"))
            out_f.write("\n\n")
    print(f"Wrote consolidated log to {consolidated}.")


def merge_batches(batch_glob: str, output_dir: str) -> None:
    batch_dirs = _find_batch_dirs(batch_glob)
    if not batch_dirs:
        print(f"No batch directories found for {batch_glob}")
        # Still merge logs even if no batch dirs found
        _merge_logs(output_dir)
        return

    all_proxies: List[Proxy] = []
    for batch_dir in batch_dirs:
        proxies_path = batch_dir / "proxies.json"
        if not proxies_path.exists():
            print(f"Missing {proxies_path}, skipping.")
            continue
        all_proxies.extend(_load_proxies_from_file(proxies_path))

    if not all_proxies:
        print("No proxies loaded; aborting merge (logs still consolidated).")
        _merge_logs(output_dir)
        return

    settings = AppSettings()
    all_proxies = dedupe_and_shuffle(all_proxies)
    if settings.ENABLE_ENDPOINT_FILTERING:
        all_proxies = filter_unique_endpoints(all_proxies)

    # Merge databases before sorting to leverage history.
    _merge_quality_db(batch_dirs)
    _merge_anomaly_db(batch_dirs)
    history = _merge_history_db(batch_dirs)
    _merge_timeout_history(batch_dirs)

    sort_proxies_pareto(all_proxies, history)

    stats_payload = _merge_metadata(batch_dirs)
    stats = PipelineStats()
    stats.total_configured_sources = int(
        stats_payload.get("total_configured_sources", 0)
    )
    stats.fetched_sources = int(stats_payload.get("fetched_sources", 0))
    stats.fetched_lines = int(stats_payload.get("fetched_lines", 0))
    stats.parsed = int(stats_payload.get("parsed", 0))
    stats.tested = int(stats_payload.get("tested", 0))
    stats.working = len(all_proxies)
    stats.geo_resolved = int(stats_payload.get("geo_resolved", 0))
    stats.cache_misses = int(stats_payload.get("cache_misses", 0))
    stats.duration = float(stats_payload.get("duration", 0.0))
    stats.revived_warp = int(stats_payload.get("revived_warp", 0))
    stats.revived_vwarp = int(stats_payload.get("revived_vwarp", 0))
    stats.vwarp_attempts = int(stats_payload.get("vwarp_attempts", 0))
    stats.vwarp_success = int(stats_payload.get("vwarp_success", 0))
    stats.drop_reasons = stats_payload.get("drop_reasons", {})
    stats.final_count = len(all_proxies)
    stats.time_limited = bool(stats_payload.get("time_limited", False))
    stats.time_limit_seconds = int(stats_payload.get("time_limit_seconds", 0) or 0)
    stats.end_time = datetime.now(timezone.utc)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    asyncio.run(
        output_handler.generate_pipeline_outputs(
            all_proxies, output_path, stats, history, washer=None
        )
    )

    _merge_logs(output_dir)
    print(f"Merged {len(all_proxies)} proxies into {output_dir}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge batch outputs.")
    parser.add_argument(
        "--batch-glob",
        default="output_batch_*",
        help="Glob pattern for batch output directories",
    )
    parser.add_argument("--output-dir", default="output", help="Output directory")
    args = parser.parse_args()

    # 1. Merge the cache history first (redundant but safe per audit)
    merge_cache_history(args.batch_glob, args.output_dir)

    merge_batches(args.batch_glob, args.output_dir)
