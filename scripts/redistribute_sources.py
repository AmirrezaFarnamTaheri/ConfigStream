#!/usr/bin/env python3
"""
Redistribute sources from all batch files into 14 balanced batches.
Ensures links from the same project are spread across shards.
"""
import glob
import os
from pathlib import Path
from urllib.parse import urlparse


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
        return url


def redistribute():
    sources_dir = Path("sources")
    all_lines = set()

    # 1. Collect all existing sources
    batch_files = glob.glob(str(sources_dir / "batch_*.txt"))
    print(f"Found {len(batch_files)} batch files.")

    for bf in batch_files:
        with open(bf, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    all_lines.add(line)

    sorted_sources = sorted(list(all_lines))
    total_sources = len(sorted_sources)
    print(f"Total unique sources found: {total_sources}")

    if total_sources == 0:
        print("No sources found. Exiting.")
        return

    # 3. Distribute into 14 batches, separating projects when possible
    num_batches = 14
    print(f"Redistributing into {num_batches} batches with project separation...")

    batches = [[] for _ in range(num_batches)]
    batch_projects = [set() for _ in range(num_batches)]
    batch_loads = [0] * num_batches

    project_groups = {}
    for url in sorted_sources:
        key = _project_key(url)
        project_groups.setdefault(key, []).append(url)

    for project, items in sorted(
        project_groups.items(), key=lambda x: len(x[1]), reverse=True
    ):
        if len(items) > num_batches:
            print(
                f"Warning: Project {project} has {len(items)} links; "
                "some shards will contain more than one link."
            )
        for url in items:
            candidate_batches = [
                i for i in range(num_batches) if project not in batch_projects[i]
            ]
            if not candidate_batches:
                candidate_batches = list(range(num_batches))
            target = min(candidate_batches, key=lambda i: batch_loads[i])
            batches[target].append(url)
            batch_projects[target].add(project)
            batch_loads[target] += 1

    for i, chunk in enumerate(batches, start=1):
        filename = sources_dir / f"batch_{i}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Batch {i} - {len(chunk)} sources\n")
            f.write("\n".join(chunk) + "\n")

        print(f"Wrote {filename} ({len(chunk)} sources)")

    # 4. Cleanup extra batches (batch_15, etc.)
    # We re-glob because we might have deleted/created things
    batch_files_final = glob.glob(str(sources_dir / "batch_*.txt"))
    for bf in batch_files_final:
        try:
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
