#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Redistribute sources among batch files based on historical runtime
to ensure uniform execution time across parallel CI jobs.
"""

import sqlite3
import statistics
import logging
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DB_PATH = Path("data/source_quality.db")
SOURCES_DIR = Path("sources")
BATCH_COUNT = 14


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


def get_source_durations(db_path: Path) -> Dict[str, float]:
    """
    Fetch average duration for each source from the database.
    """
    if not db_path.exists():
        logger.warning(f"Database {db_path} not found. Using default weights.")
        return {}

    try:
        with sqlite3.connect(db_path) as conn:
            # Check if source_runs table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='source_runs'"
            )
            if not cursor.fetchone():
                return {}

            # Get average duration for last 5 runs per source
            query = """
                SELECT url, avg(duration_ms)
                FROM (
                    SELECT url, duration_ms,
                           row_number() OVER (PARTITION BY url ORDER BY timestamp DESC) as rn
                    FROM source_runs
                )
                WHERE rn <= 5
                GROUP BY url
            """
            rows = conn.execute(query).fetchall()
            return {row[0]: row[1] for row in rows}
    except Exception as e:
        logger.error(f"Error reading database: {e}")
        return {}


def read_all_sources(sources_dir: Path) -> List[str]:
    """
    Read all sources from all batch files.
    """
    all_sources = set()
    for batch_file in sources_dir.glob("batch_*.txt"):
        try:
            with open(batch_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        all_sources.add(line)
        except Exception as e:
            logger.error(f"Error reading {batch_file}: {e}")
    return list(all_sources)


def distribute_sources(
    sources: List[str], durations: Dict[str, float], num_batches: int
) -> Dict[int, List[str]]:
    """
    Distribute sources into batches using a greedy algorithm to balance total duration.
    """
    # Default duration for unknown sources (median of known or 5000ms)
    if durations:
        default_duration = statistics.median(durations.values())
    else:
        default_duration = 5000.0

    # Create list of (source, duration)
    weighted_sources = []
    for s in sources:
        d = durations.get(s, default_duration)
        weighted_sources.append((s, d))

    # Sort by duration descending (Longest Processing Time first)
    weighted_sources.sort(key=lambda x: x[1], reverse=True)

    batches: Dict[int, List[Tuple[str, float]]] = defaultdict(list)
    batch_times: Dict[int, float] = {i: 0.0 for i in range(1, num_batches + 1)}
    batch_projects: Dict[int, Set[str]] = {
        i: set() for i in range(1, num_batches + 1)
    }

    project_groups: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for source, duration in weighted_sources:
        project_groups[_project_key(source)].append((source, duration))

    ordered_projects = sorted(
        project_groups.items(),
        key=lambda item: sum(duration for _, duration in item[1]),
        reverse=True,
    )

    for project, items in ordered_projects:
        if len(items) > num_batches:
            logger.warning(
                "Project %s has %d links; some shards will contain more than one link.",
                project,
                len(items),
            )
        for source, duration in sorted(items, key=lambda x: x[1], reverse=True):
            candidates = [i for i in batch_times if project not in batch_projects[i]]
            if not candidates:
                candidates = list(batch_times.keys())
            min_batch = min(candidates, key=lambda k: batch_times[k])
            batches[min_batch].append((source, duration))
            batch_times[min_batch] += duration
            batch_projects[min_batch].add(project)

    # Extract just the source strings
    result = {i: [x[0] for x in batch_list] for i, batch_list in batches.items()}

    # Log distribution stats
    logger.info("Batch Distribution Stats:")
    for i in range(1, num_batches + 1):
        count = len(result.get(i, []))
        total_time = batch_times[i]
        logger.info(
            f"  Batch {i}: {count} sources, ~{total_time/1000:.2f}s est. duration"
        )

    return result


def write_batches(batches: Dict[int, List[str]], sources_dir: Path):
    """
    Write sources back to batch files.
    """
    sources_dir.mkdir(parents=True, exist_ok=True)
    for i, sources_list in batches.items():
        file_path = sources_dir / f"batch_{i}.txt"
        try:
            with open(file_path, "w") as f:
                # Add header
                f.write(f"# Batch {i} - Auto-optimized\n")
                f.write("\n".join(sources_list))
                f.write("\n")
            logger.info(f"Wrote {len(sources_list)} sources to {file_path}")
        except Exception as e:
            logger.error(f"Failed to write {file_path}: {e}")


def main():
    durations = get_source_durations(DB_PATH)
    all_sources = read_all_sources(SOURCES_DIR)

    if not all_sources:
        logger.warning("No sources found to redistribute.")
        return

    logger.info(f"Found {len(all_sources)} unique sources.")
    logger.info(f"Found historical data for {len(durations)} sources.")

    batches = distribute_sources(all_sources, durations, BATCH_COUNT)
    write_batches(batches, SOURCES_DIR)


if __name__ == "__main__":
    main()
