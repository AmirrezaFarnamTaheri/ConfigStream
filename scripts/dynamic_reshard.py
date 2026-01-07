# SPDX-License-Identifier: AGPL-3.0-or-later
import re
import glob
import shutil
import statistics
import os
from pathlib import Path
from typing import Dict, List, Tuple

# --- Configuration ---
LOG_PATTERN = "*.log"  # Pattern to match your pipeline logs
SOURCES_DIR = Path("sources")  # Directory containing batch_*.txt files
BACKUP_DIR = SOURCES_DIR / "backup_dynamic"
DEFAULT_WEIGHT = 100  # Fallback weight for sources not found in logs

# Regex for Source Summary block in consumer.py
# Source Summary [URL]: Raw=123 ... Fetch=500ms Dur=1500ms
RAW_LINES_REGEX = re.compile(r"Raw=(\d+)")
FETCH_TIME_REGEX = re.compile(r"Fetch=([\d.]+)ms")


def get_current_batch_count() -> int:
    """Detect number of batch files to maintain existing parallelism."""
    count = len(list(SOURCES_DIR.glob("batch_*.txt")))
    return max(count, 10)  # Default to at least 10


def parse_logs(log_files: List[str]) -> Dict[str, Tuple[int, float]]:
    """
    Scans log files to build a map of {source_url: (proxy_count, fetch_duration)}.
    """
    source_metrics: Dict[str, Tuple[int, float]] = {}
    print(f"🔍 Scanning {len(log_files)} log files...")

    for log_file in log_files:
        try:
            text = Path(log_file).read_text(encoding="utf-8", errors="ignore")
            # We need to parse blocks. Since it's multiline, we can iterate or use robust regex.
            # Simplified: Split by "Source Summary ["
            blocks = text.split("Source Summary [")
            for block in blocks[1:]:  # Skip preamble
                try:
                    # Extract URL (up to closing ])
                    url_end = block.find("]")
                    if url_end == -1:
                        continue
                    url = block[:url_end].strip()

                    # Extract Raw Lines
                    lines_match = RAW_LINES_REGEX.search(block)
                    count = int(lines_match.group(1)) if lines_match else 0

                    # Extract Fetch Time
                    fetch_match = FETCH_TIME_REGEX.search(block)
                    fetch_ms = float(fetch_match.group(1)) if fetch_match else 0.0
                    fetch_duration = fetch_ms / 1000.0

                    if count > 0:
                        existing = source_metrics.get(url, (0, 0.0))
                        if fetch_duration > existing[1]:
                            source_metrics[url] = (count, fetch_duration)
                except Exception:
                    continue
        except Exception as e:
            print(f"⚠️  Could not read {log_file}: {e}")

    print(f"📊 Identified {len(source_metrics)} active sources from logs.")
    return source_metrics


def get_existing_sources() -> List[str]:
    """
    Reads all URLs from current source files to ensure we don't lose any
    that might have failed in the logs.
    """
    urls = set()
    if not SOURCES_DIR.exists():
        return []

    for f in SOURCES_DIR.glob("batch_*.txt"):
        try:
            content = f.read_text(encoding="utf-8").splitlines()
            for line in content:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.add(line)
        except Exception as e:
            print(f"⚠️  Could not read source file {f}: {e}")
    return list(urls)


def main() -> None:
    # 1. Setup Workspace
    log_files = glob.glob(LOG_PATTERN)

    if not SOURCES_DIR.exists():
        print(f"❌ Sources directory '{SOURCES_DIR}' not found.")
        return

    # Determine batch count dynamically
    num_batches = get_current_batch_count()
    print(f"Using {num_batches} batches based on existing files.")

    # 2. Backup
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📦 Backing up sources to {BACKUP_DIR}...")
    for f in SOURCES_DIR.glob("batch_*.txt"):
        try:
            shutil.copy2(f, BACKUP_DIR)
        except Exception as e:
            print(f"⚠️  Backup failed for {f}: {e}")

    # 3. Gather Data
    observed_metrics = parse_logs(log_files) if log_files else {}
    all_urls = get_existing_sources()

    # 4. Assign Weights Based on Fetch + Test Duration
    # Total batch time = fetch_time + test_time
    # Test time is proportional to proxy count (500 workers, ~0.03s per proxy)
    TEST_TIME_PER_PROXY = 0.03  # seconds (empirical estimate with Go tester)

    final_sources: List[Tuple[str, int]] = []
    for url in all_urls:
        if url in observed_metrics:
            count, fetch_duration = observed_metrics[url]
            # Calculate total time: fetch + testing
            # Test time = count * time_per_proxy
            test_duration = count * TEST_TIME_PER_PROXY
            total_duration = fetch_duration + test_duration

            # Convert to deciseconds for integer weights
            weight = int(total_duration * 10)
            # Ensure minimum weight of 1
            if weight == 0:
                weight = 1
        else:
            # Default: assume 10s fetch + 100 proxies * 0.03s = 10s + 3s = 13s
            weight = 130
        final_sources.append((url, weight))

    # 5. Sort by Weight (Descending) - Critical for Bin Packing
    final_sources.sort(key=lambda x: x[1], reverse=True)

    # 6. Greedy Bin Packing
    batches: List[List[str]] = [[] for _ in range(num_batches)]
    batch_loads: List[int] = [0] * num_batches

    for url, weight in final_sources:
        # Find the batch with the current lowest load
        min_load_index = batch_loads.index(min(batch_loads))

        batches[min_load_index].append(url)
        batch_loads[min_load_index] += weight

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
    print("\n⚖️  Optimized Batch Distribution (Time-Based):")
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
                print(f"🗑️ Deleted stale batch: {stale.name}")
            except Exception as e:
                print(f"⚠️ Failed to delete stale batch {stale}: {e}")

        # 2. Rename temps to final
        for tmp_path, final_path in temp_files:
            tmp_path.replace(final_path)

    except Exception as e:
        print(f"❌ Atomic write failed: {e}")
        # Cleanup temps
        for tmp, _ in temp_files:
            if tmp.exists():
                tmp.unlink()
        return

    # 9. Log Performance Metrics
    print("\n📊 Time-Based Load Balancing Metrics:")
    print(f"  Load Balance Ratio: {load_balance_ratio:.2f}x (ideal: 1.00x)")
    print(f"  Standard Deviation: {std_dev / 10:.2f}s")
    print(f"  Slowest Batch: {max_load / 10:.1f}s")
    print(f"  Fastest Batch: {min_load / 10:.1f}s")
    print(f"  Sources with timing data: {len(observed_metrics)}/{len(all_urls)}")

    print("\n✅ Refactor complete. Run the pipeline again to see performance gains.")


if __name__ == "__main__":
    main()
