# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import glob
import json
import os
from scripts.merge.core import merge_batches


def merge_cache_history(batch_glob: str, output_dir: str):
    print("--- Merging Cache History ---")
    merged_cache = {}

    # Look for cache files in batch directories
    # Note: merge_batches_async (in core.py) also does this, but keeping this
    # as a top-level guarantee as requested by the audit report
    pattern = os.path.join(batch_glob, "data", "test_cache.json")
    files = glob.glob(pattern)

    # Also look in root of batch just in case
    files.extend(glob.glob(os.path.join(batch_glob, "test_cache.json")))

    files = sorted(list(set(files)))

    print(f"Found {len(files)} cache files.")

    for fpath in files:
        try:
            with open(fpath, "r") as f:
                data = json.load(f)
                # [FIX] Smart Aggregation instead of .update()
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
    with open(out_path, "w") as f:
        json.dump(merged_cache, f)
    print(f"Total merged entries: {len(merged_cache)}")


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
