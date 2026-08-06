# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create deterministic runtime source shards and a GitHub Actions matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def partition(lines: list[str], parts: int) -> list[list[str]]:
    buckets: list[list[str]] = [[] for _ in range(parts)]
    for line in sorted(dict.fromkeys(lines)):
        index = int(hashlib.sha256(line.encode()).hexdigest(), 16) % parts
        buckets[index].append(line)
    return buckets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-dir", type=Path, default=Path("sources"))
    parser.add_argument("--output-dir", type=Path, default=Path("sources/runtime"))
    parser.add_argument("--parts", type=int, default=4)
    parser.add_argument("--matrix-output", type=Path, required=True)
    args = parser.parse_args()
    if args.parts < 1:
        raise SystemExit("--parts must be >= 1")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    matrix: list[dict[str, object]] = []
    for source_file in sorted(args.sources_dir.glob("batch_*.txt")):
        batch = source_file.stem.removeprefix("batch_")
        lines = [
            line.strip()
            for line in source_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        for part, bucket in enumerate(partition(lines, args.parts), start=1):
            if not bucket:
                continue
            target = args.output_dir / f"batch_{batch}_part_{part}.txt"
            target.write_text("\n".join(bucket) + "\n", encoding="utf-8")
            matrix.append(
                {
                    "batch": batch,
                    "part": part,
                    "source_file": target.as_posix(),
                    "source_count": len(bucket),
                    "source_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
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
