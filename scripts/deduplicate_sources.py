#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Deduplicate and deterministically rebalance the canonical source shards.

``sources/batch_*.txt`` are the only authored and operational inputs.
"""

from __future__ import annotations

from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from configstream.source_admission import normalize_source_locator

SOURCES_DIR = Path("sources")
BATCH_PATTERN = "batch_*.txt"
NUM_BATCHES = 17


def batch_sort_key(path: Path) -> tuple[int, str]:
    """Sort canonical batch paths by numeric shard index, then by name."""
    try:
        index = int(path.stem.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        index = sys.maxsize
    return index, path.name


def _read_url_lines(path: Path) -> set[str]:
    urls: set[str] = set()
    if not path.exists():
        return urls
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            urls.add(normalize_source_locator(line))
    return urls


def load_canonical_sources(sources_dir: Path = SOURCES_DIR) -> set[str]:
    """Read only the authored batch files and return their unique URL set."""
    urls: set[str] = set()
    for path in sorted(sources_dir.glob(BATCH_PATTERN)):
        urls.update(_read_url_lines(path))
    return urls


def _project_key(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    parts = [part for part in parsed.path.split("/") if part]
    if host in {"raw.githubusercontent.com", "github.com"} and len(parts) >= 2:
        return f"github:{parts[0]}/{parts[1]}"
    if host in {"gitlab.com", "bitbucket.org"} and len(parts) >= 2:
        return f"{host}:{parts[0]}/{parts[1]}"
    return host or url


def load_canonical_layout(
    sources_dir: Path = SOURCES_DIR,
    *,
    num_batches: int = NUM_BATCHES,
) -> list[list[str]]:
    """Normalize locators and keep only their first authored occurrence."""
    batches: list[list[str]] = [[] for _ in range(num_batches)]
    seen: set[str] = set()
    for index, path in enumerate(
        sorted(sources_dir.glob(BATCH_PATTERN), key=batch_sort_key)[:num_batches]
    ):
        for url in sorted(_read_url_lines(path)):
            if url not in seen:
                batches[index].append(url)
                seen.add(url)
    return batches


def rebalance_existing_layout(batches: list[list[str]]) -> list[list[str]]:
    """Balance a deduplicated layout with the fewest deterministic moves."""
    if not batches:
        raise ValueError("at least one batch is required")
    result = [sorted(dict.fromkeys(batch)) for batch in batches]
    total = sum(len(batch) for batch in result)
    base, remainder = divmod(total, len(result))
    targets = [base + (index < remainder) for index in range(len(result))]

    while True:
        recipient = next(
            (
                index
                for index, target in enumerate(targets)
                if len(result[index]) < target
            ),
            None,
        )
        if recipient is None:
            break
        donor = next(
            (
                index
                for index in reversed(range(len(result)))
                if len(result[index]) > targets[index]
            ),
            None,
        )
        if donor is None:
            raise ValueError("could not rebalance source layout")
        recipient_projects = {_project_key(url) for url in result[recipient]}
        candidates = [
            url for url in result[donor] if _project_key(url) not in recipient_projects
        ] or list(result[donor])
        moved = sorted(candidates)[-1]
        result[donor].remove(moved)
        result[recipient].append(moved)
        result[recipient].sort()
    return result


def write_source_layout(
    batches: list[list[str]],
    *,
    sources_dir: Path = SOURCES_DIR,
) -> None:
    """Write all canonical shards atomically, removing stale shard files."""
    sources_dir.mkdir(parents=True, exist_ok=True)
    expected_paths: set[Path] = set()

    for index, batch in enumerate(batches, start=1):
        path = sources_dir / f"batch_{index}.txt"
        expected_paths.add(path)
        content = [
            f"# ConfigStream Batch {index}",
            f"# Optimized Sources: {len(batch)}",
            "",
            *batch,
        ]
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text("\n".join(content) + "\n", encoding="utf-8")
        temp.replace(path)

    for stale in set(sources_dir.glob(BATCH_PATTERN)) - expected_paths:
        stale.unlink()


def main() -> int:
    batches = load_canonical_layout()
    urls = {url for batch in batches for url in batch}
    if not urls:
        print("ERROR: no canonical URLs found in sources/batch_*.txt")
        return 1

    balanced = rebalance_existing_layout(batches)
    write_source_layout(balanced)
    print(f"Wrote {len(urls)} unique sources to {len(balanced)} canonical batches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
