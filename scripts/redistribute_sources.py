#!/usr/bin/env python3
"""
Redistribute sources from all batch files (including batch 12) into 11 balanced batches.
"""
import glob
import os
import math
from pathlib import Path


def redistribute():
    sources_dir = Path("sources")
    all_lines = set()

    # 1. Collect all sources
    batch_files = glob.glob(str(sources_dir / "batch_*.txt"))
    print(f"Found {len(batch_files)} batch files.")

    for bf in batch_files:
        with open(bf, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    all_lines.add(line)

    # Add manual extras if any (e.g. Tor exit list identified in audit)
    extras = ["https://check.torproject.org/torbulkexitlist"]
    for ex in extras:
        all_lines.add(ex)

    sorted_sources = sorted(list(all_lines))
    total_sources = len(sorted_sources)
    print(f"Total unique sources found: {total_sources}")

    if total_sources == 0:
        print("No sources found. Exiting.")
        return

    # 2. Distribute into 11 batches
    num_batches = 11
    batch_size = math.ceil(total_sources / num_batches)

    print(
        f"Redistributing into {num_batches} batches (approx {batch_size} per batch)..."
    )

    # Clear existing batch files? Or overwrite? Overwrite is safer.
    # We will write batch_1.txt to batch_11.txt
    # and remove batch_12.txt if it exists.

    for i in range(num_batches):
        batch_num = i + 1
        start_idx = i * batch_size
        end_idx = start_idx + batch_size
        chunk = sorted_sources[start_idx:end_idx]

        filename = sources_dir / f"batch_{batch_num}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Batch {batch_num} - {len(chunk)} sources\n")
            f.write("\n".join(chunk) + "\n")

        print(f"Wrote {filename} ({len(chunk)} sources)")

    # 3. Cleanup extra batches (batch_12, etc.)
    for bf in batch_files:
        try:
            # Extract number
            name = Path(bf).name
            num_part = name.replace("batch_", "").replace(".txt", "")
            if num_part.isdigit():
                num = int(num_part)
                if num > num_batches:
                    print(f"Removing excess batch file: {bf}")
                    os.remove(bf)
        except Exception as e:
            print(f"Error checking/removing {bf}: {e}")


if __name__ == "__main__":
    redistribute()
