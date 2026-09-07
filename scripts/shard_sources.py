# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create deterministic runtime source shards and a GitHub Actions matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from configstream.source_admission import (
    classify_source_locator,
    normalize_source_locator,
)

QUARANTINE_FILENAME = "quarantine.txt"
TIMING_WEIGHTS_FILENAME = "source_timing_weights.json"


def source_timing_id(url: str) -> str:
    """Return the stable canonical source identity used by timing evidence."""

    canonical = normalize_source_locator(url)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _canonical_source_urls(sources_dir: Path) -> set[str]:
    """Return the exact canonical URL set used by the reshard sidecar digest."""

    urls: set[str] = set()
    for source_file in sorted(sources_dir.glob("batch_*.txt")):
        for raw_line in source_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith(("http://", "https://")):
                urls.add(normalize_source_locator(line))
    return urls


def _source_set_sha256(urls: set[str]) -> str:
    canonical_urls = {normalize_source_locator(url) for url in urls}
    return hashlib.sha256(
        ("\n".join(sorted(canonical_urls)) + "\n").encode("utf-8")
    ).hexdigest()


def partition(
    lines: list[str],
    parts: int,
    *,
    weights: dict[str, int] | None = None,
    default_weight: int = 1,
) -> list[list[str]]:
    """Deterministically balance unique inputs across shard buckets.

    When timing weights are available, inputs are source locators and use
    longest-processing-time-first (LPT) scheduling. Without timing data this
    helper remains generic: equal weights provide deterministic round-robin
    balancing without requiring the inputs themselves to be URLs.
    """

    if parts < 1:
        raise ValueError("parts must be >= 1")
    if default_weight < 1:
        raise ValueError("default_weight must be >= 1")

    normalized_weights = weights or {}
    unique_lines = sorted(dict.fromkeys(lines))
    if normalized_weights:
        weighted = [
            (
                line,
                max(
                    1,
                    int(
                        normalized_weights.get(
                            source_timing_id(line),
                            default_weight,
                        )
                    ),
                ),
            )
            for line in unique_lines
        ]
    else:
        weighted = [(line, default_weight) for line in unique_lines]
    weighted.sort(key=lambda item: (-item[1], item[0]))

    buckets: list[list[str]] = [[] for _ in range(parts)]
    loads = [0] * parts
    for line, weight in weighted:
        index = min(range(parts), key=lambda i: (loads[i], len(buckets[i]), i))
        buckets[index].append(line)
        loads[index] += weight
    return buckets


def load_timing_weights(sources_dir: Path) -> tuple[dict[str, int], int]:
    """Load the optional governed runtime timing sidecar.

    Invalid or stale sidecars fail closed because silently ignoring corrupt
    scheduling evidence would recreate the imbalance this file is meant to
    prevent.
    """

    path = sources_dir / TIMING_WEIGHTS_FILENAME
    if not path.is_file():
        return {}, 1
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid {TIMING_WEIGHTS_FILENAME}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid {TIMING_WEIGHTS_FILENAME}: expected object")
    if payload.get("schema_version") != 1 or payload.get("unit") != "deciseconds":
        raise SystemExit(f"invalid {TIMING_WEIGHTS_FILENAME}: unsupported schema")

    default_weight = payload.get("default_weight")
    raw_weights = payload.get("weights", {})
    if (
        not isinstance(default_weight, int)
        or isinstance(default_weight, bool)
        or default_weight < 1
        or not isinstance(raw_weights, dict)
    ):
        raise SystemExit(f"invalid {TIMING_WEIGHTS_FILENAME}: malformed weights")

    weights: dict[str, int] = {}
    for key, value in raw_weights.items():
        if (
            not isinstance(key, str)
            or len(key) != 64
            or any(char not in "0123456789abcdef" for char in key.lower())
            or not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise SystemExit(
                f"invalid {TIMING_WEIGHTS_FILENAME}: invalid source weight"
            )
        weights[key] = value

    canonical_urls = _canonical_source_urls(sources_dir)
    expected_digest = _source_set_sha256(canonical_urls)
    if payload.get("source_set_sha256") != expected_digest:
        raise SystemExit(f"invalid {TIMING_WEIGHTS_FILENAME}: source-set mismatch")
    allowed_ids = {source_timing_id(url) for url in canonical_urls}
    if set(weights) - allowed_ids:
        raise SystemExit(
            f"invalid {TIMING_WEIGHTS_FILENAME}: weights reference unknown sources"
        )
    return weights, default_weight


def _default_sources_dir() -> Path:
    """Return the canonical repo-root sources directory."""

    return REPO_ROOT / "sources"


def _default_output_dir() -> Path:
    """Return the canonical runtime shard directory inside the repo."""

    return _default_sources_dir() / "runtime"


def load_quarantined_sources(sources_dir: Path) -> set[str]:
    """Return explicitly quarantined source locators for runtime exclusion."""

    path = sources_dir / QUARANTINE_FILENAME
    if not path.is_file():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def active_source_lines(source_file: Path, quarantined: set[str]) -> list[str]:
    """Load active source locators while preserving the admitted batch inventory."""

    return [
        line
        for raw_line in source_file.read_text(encoding="utf-8").splitlines()
        if (line := raw_line.strip())
        and not line.lstrip().startswith("#")
        and line not in quarantined
    ]


def runtime_source_lines(source_file: Path, quarantined: set[str]) -> list[str]:
    """Return exactly the sources the scheduled CLI will attempt to fetch.

    Repository admission already validates tracked locators. Runtime sharding
    additionally excludes quarantined entries and trust classes that the CLI
    blocks by default, keeping matrix/coverage denominators aligned with actual
    source attempts.
    """

    result: list[str] = []
    for line in active_source_lines(source_file, quarantined):
        classified = classify_source_locator(line)
        if classified["trust_class"] == "insecure-transport":
            continue
        result.append(str(classified["url"]))
    return result


def _matrix_source_path(path: Path) -> str:
    """Prefer repo-relative matrix paths while preserving custom absolute paths."""

    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> int:
    """Generate runtime source shards and emit the Actions matrix payload."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-dir", type=Path, default=_default_sources_dir())
    parser.add_argument("--output-dir", type=Path, default=_default_output_dir())
    parser.add_argument("--parts", type=int, default=4)
    parser.add_argument("--matrix-output", type=Path, required=True)
    args = parser.parse_args()
    if args.parts < 1:
        raise SystemExit("--parts must be >= 1")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    quarantined = load_quarantined_sources(args.sources_dir)
    timing_weights, default_weight = load_timing_weights(args.sources_dir)
    matrix: list[dict[str, object]] = []
    for source_file in sorted(args.sources_dir.glob("batch_*.txt")):
        batch = source_file.stem.removeprefix("batch_")
        lines = runtime_source_lines(source_file, quarantined)
        for part, bucket in enumerate(
            partition(
                lines,
                args.parts,
                weights=timing_weights,
                default_weight=default_weight,
            ),
            start=1,
        ):
            if not bucket:
                continue
            target = args.output_dir / f"batch_{batch}_part_{part}.txt"
            target.write_text("\n".join(bucket) + "\n", encoding="utf-8")
            matrix.append(
                {
                    "batch": batch,
                    "part": part,
                    "source_file": _matrix_source_path(target),
                    "source_count": len(bucket),
                    "source_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                    "estimated_weight": sum(
                        max(
                            1,
                            int(
                                timing_weights.get(
                                    source_timing_id(source), default_weight
                                )
                            ),
                        )
                        for source in bucket
                    ),
                }
            )
    if not matrix:
        raise SystemExit("no source shards generated")
    payload = {"include": matrix}
    args.matrix_output.write_text(
        json.dumps(payload, separators=(",", ":")), encoding="utf-8"
    )
    print(json.dumps(payload, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
