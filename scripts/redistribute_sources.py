#!/usr/bin/env python3
"""
Redistribute sources from all batch files into 14 balanced batches.
Ensures links from the same project are spread across shards.
"""
import glob
import os
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Tuple


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


def _read_sources_from_file(path: Path) -> List[str]:
    if not path.exists():
        return []
    lines: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def _read_sources_from_batches(sources_dir: Path) -> Tuple[List[str], int]:
    batch_files = glob.glob(str(sources_dir / "batch_*.txt"))
    print(f"Found {len(batch_files)} batch files.")
    sources: List[str] = []
    for bf in batch_files:
        with open(bf, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if line and not line.startswith("#"):
                    sources.append(line)
    return sources, len(batch_files)


def redistribute():
    sources_dir = Path("sources")
    consolidated_file = Path("consolidated_sources.txt")

    # 1. Collect all existing sources
    sources = _read_sources_from_file(consolidated_file)
    batch_count = 0
    if sources:
        print(f"Loaded {len(sources)} sources from {consolidated_file}.")
    else:
        sources, batch_count = _read_sources_from_batches(sources_dir)
        print(f"Loaded {len(sources)} sources from {batch_count} batch files.")

    total_sources = len(sources)
    unique_sources = len(set(sources))
    print(f"Total sources: {total_sources} (unique: {unique_sources})")

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
    for url in sources:
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
