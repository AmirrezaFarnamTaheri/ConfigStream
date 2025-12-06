import re
import glob
import shutil
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set

logger = logging.getLogger(__name__)

# --- Configuration ---
LOG_PATTERN = "*.log"  # Pattern to match your pipeline logs
SOURCES_DIR = Path("sources")  # Directory containing batch_*.txt files
BACKUP_DIR = SOURCES_DIR / "backup_dynamic"
NUM_BATCHES = 10  # Target number of shards
DEFAULT_WEIGHT = 100  # Fallback weight for sources not found in logs

# Strike system configuration
MAX_STRIKES = 3
MIN_SUCCESS_RATE = 0.01  # 1%
STRIKE_CACHE_PATH = Path("data/source_strikes.json")

# Regex to parse the rich logger output
# Matches: "[fetch_success] Fetched 129 proxies from https://..."
# Updated to match across newlines for wrapped logs
LOG_REGEX = re.compile(r"Fetched\s+(\d+)\s+proxies\s+from\s+[\s\n\r]+(https?://\S+)")

# Matches Source Summary for strike system
# Source Summary [https://example.com/sub]: ... Working: 5 ...
SUMMARY_REGEX = re.compile(r"Source Summary \[(https?://[^\]]+)\]:.*?Working:\s+(\d+)", re.DOTALL)


def parse_logs(log_files: List[str]) -> Tuple[Dict[str, int], Dict[str, Dict]]:
    """
    Scans log files to build a map of weights and performance stats.
    Returns: (source_weights, source_stats)
    """
    source_weights: Dict[str, int] = {}
    source_stats: Dict[str, Dict] = {}
    print(f"🔍 Scanning {len(log_files)} log files...")

    for log_file in log_files:
        try:
            # Read full content instead of line-by-line
            text = Path(log_file).read_text(encoding="utf-8", errors="ignore")

            # Parse Weights (Fetched Count)
            for match in LOG_REGEX.finditer(text):
                count = int(match.group(1))
                url = match.group(2).strip()
                if count > source_weights.get(url, 0):
                    source_weights[url] = count

            # Parse Performance (Working Count) for Strikes
            for match in SUMMARY_REGEX.finditer(text):
                url = match.group(1).strip()
                working = int(match.group(2))

                if url not in source_stats:
                    source_stats[url] = {"working": 0, "fetched": 0}

                # Update with latest run data (or aggregate if multiple logs)
                source_stats[url]["working"] = max(source_stats[url]["working"], working)

        except Exception as e:
            print(f"⚠️  Could not read {log_file}: {e}")

    # Backfill fetched count into stats from weights
    for url, count in source_weights.items():
        if url in source_stats:
            source_stats[url]["fetched"] = count
        else:
            source_stats[url] = {"working": 0, "fetched": count}

    print(f"📊 Identified {len(source_weights)} active sources from logs.")
    return source_weights, source_stats

def load_strikes() -> Dict[str, int]:
    """Load strike counts from cache."""
    try:
        if STRIKE_CACHE_PATH.exists():
            return json.loads(STRIKE_CACHE_PATH.read_text())
    except Exception:
        pass
    return {}

def save_strikes(strikes: Dict[str, int]) -> None:
    """Save strike counts to cache."""
    try:
        STRIKE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STRIKE_CACHE_PATH.write_text(json.dumps(strikes, indent=2))
    except Exception as e:
        logger.warning(f"Could not save strikes: {e}")

def update_strikes(source_stats: Dict[str, Dict], strikes: Dict[str, int]) -> Set[str]:
    """Update strike counts and return sources to disable."""
    disabled = set()

    for url, data in source_stats.items():
        working = data.get("working", 0)
        fetched = data.get("fetched", 0)
        success_rate = working / fetched if fetched > 0 else 0

        # Only strike if we fetched a significant amount (e.g. > 10) but got nothing/little
        if fetched > 10 and success_rate < MIN_SUCCESS_RATE:
            strikes[url] = strikes.get(url, 0) + 1
            if strikes[url] >= MAX_STRIKES:
                print(f"🚫 Disabling source (strike {strikes[url]}): {url}")
                disabled.add(url)
        elif success_rate >= MIN_SUCCESS_RATE:
            if strikes.get(url, 0) > 0:
                print(f"✅ Resetting strikes for {url} (Success: {success_rate:.1%})")
            strikes[url] = 0  # Reset on success

    return disabled


def get_existing_sources() -> List[str]:
    """
    Reads all URLs from current source files to ensure we don't lose any
    that might have failed in the logs.
    """
    urls = set()
    if not SOURCES_DIR.exists():
        return []

    for f in SOURCES_DIR.glob("batch_*.txt"):
        content = f.read_text(encoding="utf-8").splitlines()
        for line in content:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.add(line)
    return list(urls)


def main() -> None:
    # 1. Setup Workspace
    log_files = glob.glob(LOG_PATTERN)
    if not log_files:
        print(f"❌ No log files found matching '{LOG_PATTERN}'. Cannot optimize!")
        return

    if not SOURCES_DIR.exists():
        print(f"❌ Sources directory '{SOURCES_DIR}' not found.")
        return

    # 2. Backup
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📦 Backing up sources to {BACKUP_DIR}...")
    for f in SOURCES_DIR.glob("batch_*.txt"):
        shutil.copy2(f, BACKUP_DIR)

    # 3. Gather Data
    observed_weights, source_stats = parse_logs(log_files)
    all_urls = get_existing_sources()

    # 4. Apply Strike System
    strikes = load_strikes()
    disabled_sources = update_strikes(source_stats, strikes)
    save_strikes(strikes)

    # 5. Assign Weights & Filter
    final_sources: List[Tuple[str, int]] = []
    for url in all_urls:
        if url in disabled_sources:
            continue

        weight = observed_weights.get(url, DEFAULT_WEIGHT)
        # If weight is 0 (empty source), treat it as small but non-zero to keep it checked
        if weight == 0:
            weight = 10
        final_sources.append((url, weight))

    # 6. Sort by Weight (Descending) - Critical for Bin Packing
    final_sources.sort(key=lambda x: x[1], reverse=True)

    # 6. Greedy Bin Packing
    batches: List[List[str]] = [[] for _ in range(NUM_BATCHES)]
    batch_loads: List[int] = [0] * NUM_BATCHES

    for url, weight in final_sources:
        # Find the batch with the current lowest load
        min_load_index = batch_loads.index(min(batch_loads))

        batches[min_load_index].append(url)
        batch_loads[min_load_index] += weight

    # 7. Write Output
    print("\n⚖️  Optimized Batch Distribution:")
    print(f"{'Batch':<10} | {'Sources':<10} | {'Est. Proxies':<15}")
    print("-" * 40)

    for i, batch in enumerate(batches):
        file_path = SOURCES_DIR / f"batch_{i+1}.txt"

        # Header info
        est_load = batch_loads[i]
        content = [
            f"# ConfigStream Batch {i+1}",
            "# Optimized based on run-time logs",
            f"# Est. Load: {est_load} proxies",
            "",
        ]
        content.extend(batch)

        file_path.write_text("\n".join(content), encoding="utf-8")
        print(f"Batch {i+1:<4} | {len(batch):<10} | {est_load:<15}")

    print("\n✅ Refactor complete. Run the pipeline again to see performance gains.")


if __name__ == "__main__":
    main()
