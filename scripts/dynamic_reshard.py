import re
import glob
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# --- Configuration ---
LOG_PATTERN = "*.log"  # Pattern to match your pipeline logs
SOURCES_DIR = Path("sources")  # Directory containing batch_*.txt files
BACKUP_DIR = SOURCES_DIR / "backup_dynamic"
NUM_BATCHES = 10  # Target number of shards
DEFAULT_WEIGHT = 100  # Fallback weight for sources not found in logs

# Regex to parse the rich logger output
# Matches: "[fetch_success] Fetched 129 proxies from https://..."
LOG_REGEX = re.compile(r"Fetched\s+(\d+)\s+proxies\s+from\s+(https?://\S+)")


def parse_logs(log_files: List[str]) -> Dict[str, int]:
    """
    Scans log files to build a map of {source_url: proxy_count}.
    """
    source_weights: Dict[str, int] = {}
    print(f"🔍 Scanning {len(log_files)} log files...")

    for log_file in log_files:
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    match = LOG_REGEX.search(line)
                    if match:
                        count = int(match.group(1))
                        url = match.group(2).strip()
                        # Keep the highest count if seen multiple times (conservative estimate)
                        if count > source_weights.get(url, 0):
                            source_weights[url] = count
        except Exception as e:
            print(f"⚠️  Could not read {log_file}: {e}")

    print(f"📊 Identified {len(source_weights)} active sources from logs.")
    return source_weights


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
    observed_weights = parse_logs(log_files)
    all_urls = get_existing_sources()

    # 4. Assign Weights
    # If a URL was in the logs, use its observed count. Otherwise, use default.
    final_sources: List[Tuple[str, int]] = []
    for url in all_urls:
        weight = observed_weights.get(url, DEFAULT_WEIGHT)
        # If weight is 0 (empty source), treat it as small but non-zero to keep it checked
        if weight == 0:
            weight = 10
        final_sources.append((url, weight))

    # 5. Sort by Weight (Descending) - Critical for Bin Packing
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
