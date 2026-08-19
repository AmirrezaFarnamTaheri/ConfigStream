# SPDX-License-Identifier: AGPL-3.0-or-later
import importlib
import logging
import re
import glob
import hashlib
import shutil
import statistics
import json
import math

import sqlite3
from collections import defaultdict
from urllib.parse import urlparse
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Sequence, Set, Tuple, cast
from itertools import combinations

# --- Configuration ---
LOG_PATTERNS = [
    "output/consolidated_pipeline.log",  # Merge stage writes here
    "pipeline_batch_*.log",
    "*.log",
]  # Patterns to match pipeline logs
SOURCES_DIR = Path("sources")  # Directory containing batch_*.txt files
BACKUP_DIR = SOURCES_DIR / "backup_dynamic"
DB_PATH = Path("data/source_quality.db")
FINGERPRINT_DIR = Path("data/fingerprints")
TIMING_EVIDENCE_PATH = Path("pipeline-evidence/source_timing.jsonl")
DEFAULT_WEIGHT = 130  # Fallback weight for sources not found in logs (deciseconds)
MIN_BATCHES = 14
MAX_BATCHES = 17
TARGET_BATCH_SECONDS = 14400  # Aim for <= 4 hours per batch
RUNS_PER_SOURCE = 5

# Regex for Source Summary block in consumer.py
# Source Summary [URL]: Raw=123 ... Fetch=500ms Dur=1500ms
RAW_LINES_REGEX = re.compile(r"Raw=(\d+)")
FETCH_TIME_REGEX = re.compile(r"Fetch=([\d.]+)ms")
FETCH_TIME_COLON_REGEX = re.compile(r"Fetch:\s*([\d.]+)ms")
DURATION_REGEX = re.compile(r"Dur=([\d.]+)ms")


class StageEvidenceModule(Protocol):
    def main(self, argv: Sequence[str] | None = None) -> int: ...


def _normalize_source_key(url: str) -> str:
    if not url:
        return ""
    cleaned = url.strip()
    cleaned = cleaned.replace("[MASKED]", "")
    cleaned = cleaned.replace("[BASE64]", "")
    cleaned = cleaned.split("#", 1)[0]
    cleaned = cleaned.split("?", 1)[0]
    return cleaned.rstrip()


def _source_timing_id(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


def parse_timing_evidence(
    path: Path, allowed_urls: Set[str]
) -> Dict[str, Tuple[int, float]]:
    if not path.exists():
        return {}
    by_id = {_source_timing_id(url): url for url in allowed_urls}
    metrics: Dict[str, Tuple[int, float]] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            source_url = by_id.get(str(payload.get("source_id", "")))
            raw = int(payload.get("raw", 0) or 0)
            duration_ms = float(payload.get("duration_ms", 0.0) or 0.0)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        if not source_url or not math.isfinite(duration_ms) or duration_ms <= 0:
            continue
        duration = duration_ms / 1000.0
        existing = metrics.get(source_url, (0, 0.0))
        if duration > existing[1]:
            metrics[source_url] = (raw, duration)
    return metrics


def get_current_batch_count() -> int:
    """Detect number of batch files to maintain existing parallelism."""
    count = len(list(SOURCES_DIR.glob("batch_*.txt")))
    return max(count, MIN_BATCHES)


def _project_key(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().replace("www.", "")
        parts = [p for p in parsed.path.split("/") if p]
        if host in ("raw.githubusercontent.com", "github.com"):
            if len(parts) >= 2:
                return f"github:{parts[0]}/{parts[1]}"
        if host in ("gitlab.com", "bitbucket.org") and len(parts) >= 2:
            return f"{host}:{parts[0]}/{parts[1]}"
        return host or url
    except Exception:
        logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
        return url


def parse_logs(
    log_files: List[str],
    test_time_per_proxy: float,
    allowed_urls: Optional[set[str]] = None,
    normalized_map: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Tuple[int, float]]:
    """
    Scans log files to build a map of {source_url: (proxy_count, total_duration)}.
    """
    source_metrics: Dict[str, Tuple[int, float]] = {}
    print(f"[INFO] Scanning {len(log_files)} log files...")

    for log_file in log_files:
        try:
            text = Path(log_file).read_text(encoding="utf-8", errors="ignore")
            # We need to parse blocks. Since it's multiline, we can iterate or use robust regex.
            # Simplified: Split by "Source Summary ["
            blocks = text.split("Source Summary [")
            for block in blocks[1:]:  # Skip preamble
                try:
                    # Extract URL (up to closing ])
                    url_end = block.find("]:")
                    if url_end == -1:
                        url_end = block.find("]")
                    if url_end == -1:
                        continue
                    url = block[:url_end].strip()
                    if allowed_urls is not None and url not in allowed_urls:
                        # Attempt to map sanitized URL to real sources
                        norm = _normalize_source_key(url)
                        if normalized_map and norm in normalized_map:
                            # We'll handle later by applying metrics to mapped sources
                            pass
                        else:
                            # Fallback: prefix match (handles masked/base64 URL segments)
                            prefix = url.split("[BASE64]", 1)[0].strip()
                            if not prefix or not allowed_urls:
                                continue

                    # Extract Raw Lines
                    lines_match = RAW_LINES_REGEX.search(block)
                    count = int(lines_match.group(1)) if lines_match else 0

                    # Extract Duration (preferred)
                    dur_match = DURATION_REGEX.search(block)
                    if dur_match:
                        total_duration = float(dur_match.group(1)) / 1000.0
                    else:
                        # Extract Fetch Time (fallback)
                        fetch_match = FETCH_TIME_COLON_REGEX.search(block)
                        if not fetch_match:
                            fetch_match = FETCH_TIME_REGEX.search(block)
                        fetch_ms = float(fetch_match.group(1)) if fetch_match else 0.0
                        fetch_duration = fetch_ms / 1000.0
                        test_duration = count * test_time_per_proxy
                        total_duration = fetch_duration + test_duration

                    if total_duration > 0:
                        # Prefer direct match
                        if allowed_urls is None or url in allowed_urls:
                            existing = source_metrics.get(url, (0, 0.0))
                            if total_duration > existing[1]:
                                source_metrics[url] = (count, total_duration)
                        elif normalized_map:
                            norm = _normalize_source_key(url)
                            candidates = normalized_map.get(norm, [])
                            if candidates:
                                for candidate in candidates:
                                    existing = source_metrics.get(candidate, (0, 0.0))
                                    if total_duration > existing[1]:
                                        source_metrics[candidate] = (
                                            count,
                                            total_duration,
                                        )
                            else:
                                if allowed_urls:
                                    prefix = url.split("[BASE64]", 1)[0].strip()
                                    if prefix:
                                        candidates = [
                                            u
                                            for u in allowed_urls
                                            if u.startswith(prefix)
                                        ]
                                        if candidates:
                                            duration = total_duration / max(
                                                len(candidates), 1
                                            )
                                            count_each = (
                                                int(count / max(len(candidates), 1))
                                                if count
                                                else 0
                                            )
                                            for candidate in candidates:
                                                existing = source_metrics.get(
                                                    candidate, (0, 0.0)
                                                )
                                                if duration > existing[1]:
                                                    source_metrics[candidate] = (
                                                        count_each,
                                                        duration,
                                                    )
                            prefix = url.split("[BASE64]", 1)[0].strip()
                            if prefix:
                                candidates = [
                                    u for u in allowed_urls if u.startswith(prefix)
                                ]
                                if candidates:
                                    duration = total_duration / max(len(candidates), 1)
                                    count_each = (
                                        int(count / max(len(candidates), 1))
                                        if count
                                        else 0
                                    )
                                    for candidate in candidates:
                                        existing = source_metrics.get(
                                            candidate, (0, 0.0)
                                        )
                                        if duration > existing[1]:
                                            source_metrics[candidate] = (
                                                count_each,
                                                duration,
                                            )
                except Exception:  # nosec B112
                    logging.getLogger(__name__).debug(
                        "Suppressed broad exception", exc_info=True
                    )
                    continue
        except Exception as e:
            print(f"[WARN] Could not read {log_file}: {e}")

    print(f"[INFO] Identified {len(source_metrics)} active sources from logs.")
    return source_metrics


def parse_db_runs(
    db_path: Path, allowed_urls: Optional[set[str]] = None
) -> Tuple[Dict[str, Tuple[int, float]], Dict[str, Dict[str, float]]]:
    """
    Load recent per-source timing data from source_quality.db.

    Returns:
        source_metrics: {url: (fetched_count, avg_duration_seconds)}
        batch_stats: {batch_id: {"sources": int, "total_duration_s": float, "total_fetched": int}}
    """
    if not db_path.exists():
        return {}, {}

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='source_runs'"
            )
            if not cursor.fetchone():
                return {}, {}

            rows = conn.execute("""
                SELECT url, timestamp, duration_ms, fetched_count, working_count, batch_source
                FROM source_runs
                """).fetchall()
    except Exception as e:
        print(f"[WARN] Failed to read {db_path}: {e}")
        return {}, {}

    per_url_runs: Dict[str, List[Tuple[int, float, int, int, str]]] = defaultdict(list)
    for url, ts, duration_ms, fetched_count, working_count, batch_source in rows:
        if not url:
            continue
        if allowed_urls is not None and url not in allowed_urls:
            continue
        try:
            ts_i = int(ts or 0)
        except Exception:
            logging.getLogger(__name__).debug(
                "Suppressed broad exception", exc_info=True
            )
            ts_i = 0
        try:
            dur_ms = float(duration_ms or 0.0)
        except Exception:
            logging.getLogger(__name__).debug(
                "Suppressed broad exception", exc_info=True
            )
            dur_ms = 0.0
        try:
            fetched = int(fetched_count or 0)
        except Exception:
            logging.getLogger(__name__).debug(
                "Suppressed broad exception", exc_info=True
            )
            fetched = 0
        try:
            working = int(working_count or 0)
        except Exception:
            logging.getLogger(__name__).debug(
                "Suppressed broad exception", exc_info=True
            )
            working = 0
        batch_tag = str(batch_source or "").strip()
        per_url_runs[url].append((ts_i, dur_ms, fetched, working, batch_tag))

    source_metrics: Dict[str, Tuple[int, float]] = {}
    batch_stats: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"sources": 0, "total_duration_s": 0.0, "total_fetched": 0}
    )

    for url, runs in per_url_runs.items():
        runs.sort(key=lambda r: r[0], reverse=True)
        recent = runs[:RUNS_PER_SOURCE]
        if not recent:
            continue
        avg_duration_s = sum(r[1] for r in recent) / max(len(recent), 1) / 1000.0
        avg_fetched = int(sum(r[2] for r in recent) / max(len(recent), 1))
        source_metrics[url] = (avg_fetched, max(0.0, avg_duration_s))

        # For batch stats, use the latest run only.
        ts_i, dur_ms, fetched, _working, batch_tag = runs[0]
        if batch_tag.startswith("batch_"):
            batch_stats[batch_tag]["sources"] += 1
            batch_stats[batch_tag]["total_duration_s"] += max(0.0, dur_ms / 1000.0)
            batch_stats[batch_tag]["total_fetched"] += int(fetched)

    return source_metrics, batch_stats


def _write_batch_stats(batch_stats: Dict[str, Dict[str, float]]) -> None:
    if not batch_stats:
        return
    output = {}
    for batch_id, data in batch_stats.items():
        output[batch_id] = {
            "sources": int(data.get("sources", 0)),
            "total_duration_s": float(data.get("total_duration_s", 0.0)),
            "total_fetched": int(data.get("total_fetched", 0)),
        }
    out_path = Path("data") / "batch_load_stats.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")


def _recommend_batch_count(total_seconds: float, current_batches: int) -> int:
    if total_seconds <= 0:
        return current_batches
    required = int(math.ceil(total_seconds / TARGET_BATCH_SECONDS))
    required = max(required, MIN_BATCHES, current_batches)
    return min(required, MAX_BATCHES)


def _distribute_sources(
    final_sources: List[Tuple[str, int]], num_batches: int
) -> Tuple[List[List[str]], List[int]]:
    batches: List[List[str]] = [[] for _ in range(num_batches)]
    batch_loads: List[int] = [0] * num_batches
    batch_projects: List[set[str]] = [set() for _ in range(num_batches)]

    project_groups: Dict[str, List[Tuple[str, int]]] = {}
    for url, weight in final_sources:
        key = _project_key(url)
        project_groups.setdefault(key, []).append((url, weight))

    ordered_projects = sorted(
        project_groups.items(),
        key=lambda item: sum(weight for _, weight in item[1]),
        reverse=True,
    )

    for project, items in ordered_projects:
        if len(items) > num_batches:
            print(
                f"[WARN] Project {project} has {len(items)} sources; "
                "some shards will contain more than one link."
            )
        for url, weight in sorted(items, key=lambda x: x[1], reverse=True):
            candidate_batches = [
                i for i in range(num_batches) if project not in batch_projects[i]
            ]
            if not candidate_batches:
                candidate_batches = list(range(num_batches))
            min_load_index = min(candidate_batches, key=lambda i: batch_loads[i])
            batches[min_load_index].append(url)
            batch_loads[min_load_index] += weight
            batch_projects[min_load_index].add(project)

    return batches, batch_loads


def get_existing_sources() -> List[str]:
    """
    Reads all URLs from current source files to ensure we don't lose any
    that might have failed in the logs.
    """
    urls = set()
    invalid_count = 0
    if not SOURCES_DIR.exists():
        return []

    for f in SOURCES_DIR.glob("batch_*.txt"):
        try:
            content = f.read_text(encoding="utf-8").splitlines()
            for line in content:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("http://") or line.startswith("https://"):
                    urls.add(line)
                else:
                    invalid_count += 1
        except Exception as e:
            print(f"[WARN] Could not read source file {f}: {e}")
    if invalid_count:
        print(f"[WARN] Skipped {invalid_count} invalid lines in sources/batch_*.txt")
    return list(urls)


def analyze_similarity(observed_metrics: Dict[str, Tuple[int, float]]) -> Set[str]:
    """
    Analyzes source fingerprints to find duplicates/redundancies.
    Returns a set of URLs to remove.
    """
    print("\n[INFO] Starting Source Similarity Analysis...")
    if not FINGERPRINT_DIR.exists():
        print("[WARN] No fingerprint directory found. Skipping analysis.")
        return set()

    fingerprints: Dict[str, Set[str]] = {}

    # 1. Load Fingerprints
    count = 0
    for fp_file in FINGERPRINT_DIR.glob("*.json"):
        try:
            data = json.loads(fp_file.read_text(encoding="utf-8"))
            url = data.get("url")
            proxies = set(data.get("proxies", []))
            if url and proxies:
                fingerprints[url] = proxies
                count += 1
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug(
                "Suppressed broad exception", exc_info=True
            )
            pass

    print(f"[INFO] Loaded {count} source fingerprints.")
    if count < 2:
        return set()

    to_remove: Set[str] = set()

    # 2. Pairwise Comparison
    # Note: O(N^2) complexity. If sources > 1000, this might be slow.
    # We can optimize by bucketing or MinHash if needed, but N ~ 200-300 is fine.

    urls = list(fingerprints.keys())

    for url_a, url_b in combinations(urls, 2):
        if url_a in to_remove or url_b in to_remove:
            continue

        set_a = fingerprints[url_a]
        set_b = fingerprints[url_b]

        len_a = len(set_a)
        len_b = len(set_b)

        if len_a == 0 or len_b == 0:
            continue

        intersection = len(set_a.intersection(set_b))

        # Logic: If overlap is > 90% of the SMALLER set, the smaller one is redundant.
        # This covers:
        # 1. Exact duplicates (overlap = len_a = len_b) -> 100%
        # 2. Subset (set_a inside set_b) -> intersection = len_a -> 100%
        # 3. Near duplicate (>90% similar)

        smaller_len = min(len_a, len_b)
        overlap_ratio = intersection / smaller_len if smaller_len > 0 else 0

        if overlap_ratio > 0.90:
            # Decide which to remove
            remove_candidate = None
            keep_candidate = None
            reason = ""

            # Prefer to keep the larger set (superset)
            if len_a > len_b:
                remove_candidate = url_b
                keep_candidate = url_a
                reason = f"Subset/High Overlap ({overlap_ratio:.1%}) of larger source ({len_a} vs {len_b})"
            elif len_b > len_a:
                remove_candidate = url_a
                keep_candidate = url_b
            else:
                # Same size. Tie-break using observed metrics (working count/reliability)
                metric_a = observed_metrics.get(url_a, (0, 0))  # (fetched, duration)

                dur_a = metric_a[1]
                dur_b = observed_metrics.get(url_b, (0, 0))[1]

                if dur_a < dur_b:
                    remove_candidate = url_b
                    keep_candidate = url_a
                    reason = f"Duplicate ({overlap_ratio:.1%}), slower fetch ({dur_b:.1f}s vs {dur_a:.1f}s)"
                else:
                    remove_candidate = url_a
                    keep_candidate = url_b
                    reason = f"Duplicate ({overlap_ratio:.1%}), slower fetch ({dur_a:.1f}s vs {dur_b:.1f}s)"

            if remove_candidate:
                to_remove.add(remove_candidate)
                print(
                    f"[REMOVE] {remove_candidate}\n  -> Reason: {reason} (Kept: {keep_candidate})"
                )

    print(f"[INFO] Analysis complete. Marked {len(to_remove)} sources for removal.")
    return to_remove


def main() -> None:
    _require_timing_prerequisites()
    log_files: List[str] = []
    for pattern in LOG_PATTERNS:
        log_files.extend(glob.glob(pattern))
    log_files = sorted(set(log_files))

    if not SOURCES_DIR.exists():
        print(f"[ERROR] Sources directory '{SOURCES_DIR}' not found.")
        raise SystemExit(1)

    # Determine batch count dynamically
    num_batches = get_current_batch_count()
    print(f"Using {num_batches} batches based on existing files.")

    # 2. Backup
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Backing up sources to {BACKUP_DIR}...")
    for f in SOURCES_DIR.glob("batch_*.txt"):
        try:
            shutil.copy2(f, BACKUP_DIR)
        except Exception as e:
            print(f"[WARN] Backup failed for {f}: {e}")

    # 3. Gather Data
    all_urls = set(get_existing_sources())
    if not all_urls:
        print("[ERROR] No sources found in sources/batch_*.txt")
        raise SystemExit(1)
    normalized_map: Dict[str, List[str]] = defaultdict(list)
    for url in all_urls:
        key = _normalize_source_key(url)
        if key:
            normalized_map[key].append(url)

    # Test time is proportional to proxy count (500 workers, ~0.03s per proxy)
    TEST_TIME_PER_PROXY = 0.03  # seconds (empirical estimate with Go tester)
    db_metrics, batch_stats = parse_db_runs(DB_PATH, allowed_urls=all_urls)
    observed_metrics: Dict[str, Tuple[int, float]] = {}
    if log_files:
        observed_metrics.update(
            parse_logs(
                log_files,
                test_time_per_proxy=TEST_TIME_PER_PROXY,
                allowed_urls=all_urls,
                normalized_map=normalized_map,
            )
        )
    structured_metrics = parse_timing_evidence(TIMING_EVIDENCE_PATH, all_urls)
    if structured_metrics:
        observed_metrics.update(structured_metrics)
    if db_metrics:
        # Prefer DB metrics when available
        observed_metrics.update(db_metrics)
    if batch_stats:
        _write_batch_stats(batch_stats)
    all_urls = set(all_urls)

    # --- SIMILARITY ANALYSIS ---
    removed_sources = analyze_similarity(observed_metrics)
    all_urls = all_urls - removed_sources
    # ---------------------------

    # 4. Assign Weights Based on Fetch + Test Duration

    final_sources: List[Tuple[str, int]] = []
    for url in all_urls:
        if url in observed_metrics:
            count, total_duration = observed_metrics[url]
            # Convert to deciseconds for integer weights
            weight = int(total_duration * 10)
            # Ensure minimum weight of 1
            if weight == 0:
                weight = 1
        else:
            # Default: assume 10s fetch + 100 proxies * 0.03s = 10s + 3s = 13s
            weight = DEFAULT_WEIGHT
        final_sources.append((url, weight))

    # 5. Sort by Weight (Descending) - Critical for Bin Packing
    final_sources.sort(key=lambda x: x[1], reverse=True)

    # 6. Greedy Bin Packing with project separation
    total_seconds = sum(weight for _, weight in final_sources) / 10.0
    recommended_batches = _recommend_batch_count(total_seconds, num_batches)
    if recommended_batches > num_batches:
        print(
            f"[INFO] Increasing batch count from {num_batches} to {recommended_batches} "
            f"(target {TARGET_BATCH_SECONDS}s max per batch)."
        )
        num_batches = recommended_batches

    batches, batch_loads = _distribute_sources(final_sources, num_batches)

    # 7. Calculate Performance Metrics
    if batch_loads:
        max_load = max(batch_loads)
        min_load = min(batch_loads)
        load_balance_ratio = max_load / min_load if min_load > 0 else float("inf")
        std_dev = statistics.stdev(batch_loads) if len(batch_loads) > 1 else 0.0
    else:
        load_balance_ratio = 0.0
        std_dev = 0.0
        max_load = 0
        min_load = 0

    # 8. Write Output
    print("\n[INFO] Optimized Batch Distribution (Time-Based):")
    print(f"{'Batch':<10} | {'Sources':<10} | {'Est. Time (s)':<15}")
    print("-" * 45)

    # Atomic Write: Write all to .tmp first, then delete original/rename
    # Also identify stale batches to delete
    existing_batches = set(SOURCES_DIR.glob("batch_*.txt"))
    new_batches = set()

    temp_files = []
    try:
        for i, batch in enumerate(batches):
            file_name = f"batch_{i+1}.txt"
            file_path = SOURCES_DIR / file_name
            new_batches.add(file_path)
            temp_path = SOURCES_DIR / (file_name + ".tmp")

            # Convert weight back to seconds for display
            est_time = batch_loads[i] / 10.0
            content = [
                f"# ConfigStream Batch {i+1}",
                "# Optimized based on fetch duration for equal execution times",
                f"# Est. Fetch Time: {est_time:.1f}s",
                "",
            ]
            content.extend(batch)

            temp_path.write_text("\n".join(content), encoding="utf-8")
            temp_files.append((temp_path, file_path))
            print(f"Batch {i+1:<4} | {len(batch):<10} | {est_time:<15.1f}")

        # If all writes successful:
        # 1. Delete stale batches (existing but not in new)
        stale_batches = existing_batches - new_batches
        for stale in stale_batches:
            try:
                stale.unlink()
                print(f"[INFO] Deleted stale batch: {stale.name}")
            except Exception as e:
                print(f"[WARN] Failed to delete stale batch {stale}: {e}")

        # 2. Rename temps to final
        for tmp_path, final_path in temp_files:
            tmp_path.replace(final_path)

    except Exception as e:
        print(f"[ERROR] Atomic write failed: {e}")
        # Cleanup temps
        for tmp, _ in temp_files:
            if tmp.exists():
                tmp.unlink()
        raise SystemExit(1)

    # 9. Log Performance Metrics
    print("\n[INFO] Time-Based Load Balancing Metrics:")
    print(f"  Load Balance Ratio: {load_balance_ratio:.2f}x (ideal: 1.00x)")
    print(f"  Standard Deviation: {std_dev / 10:.2f}s")
    print(f"  Slowest Batch: {max_load / 10:.1f}s")
    print(f"  Fastest Batch: {min_load / 10:.1f}s")
    print(f"  Sources with timing data: {len(observed_metrics)}/{len(all_urls)}")
    print(f"  Sources removed by similarity analysis: {len(removed_sources)}")

    if batch_stats:
        print("\n[INFO] Observed Batch Load (latest runs):")
        for batch_id in sorted(batch_stats.keys()):
            data = batch_stats[batch_id]
            print(
                f"  {batch_id}: {int(data['sources'])} sources, "
                f"{data['total_duration_s']:.1f}s total"
            )

    print(
        "\n[INFO] Refactor complete. Run the pipeline again to see performance gains."
    )


def _require_timing_prerequisites() -> None:
    try:
        stage_evidence = cast(
            StageEvidenceModule,
            importlib.import_module("scripts.require_stage_evidence"),
        )
    except ModuleNotFoundError as exc:
        # ``python scripts/dynamic_reshard.py`` puts the scripts directory, not
        # the repository root, on sys.path. Fall back to the sibling module for
        # that supported direct-script invocation, while preserving package
        # imports for ``python -m scripts.dynamic_reshard`` and unit tests.
        if exc.name != "scripts":
            raise
        stage_evidence = cast(
            StageEvidenceModule,
            importlib.import_module("require_stage_evidence"),
        )

    exit_code = stage_evidence.main(
        [
            "--stage",
            "normalize-source-timings",
            "--required-file",
            "source_timing_normalized.log",
            "--required-file",
            "pipeline-evidence/source_timing.jsonl",
            "--output",
            "pipeline-evidence/reshard-prerequisites.json",
        ]
    )
    if exit_code != 0:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
