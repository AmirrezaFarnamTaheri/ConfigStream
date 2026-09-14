# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

from scripts import dynamic_reshard, shard_sources
from scripts.source_shard_policy import (
    CANONICAL_BATCH_TARGET_SECONDS,
    RUNTIME_SHARD_HARD_LIMIT_SECONDS,
    RUNTIME_SHARD_PARTS,
    RUNTIME_SHARD_SOFT_LIMIT_SECONDS,
)


def test_dynamic_reshard_uses_canonical_runtime_capacity() -> None:
    assert dynamic_reshard.TARGET_BATCH_SECONDS == CANONICAL_BATCH_TARGET_SECONDS
    assert CANONICAL_BATCH_TARGET_SECONDS == (
        RUNTIME_SHARD_PARTS * RUNTIME_SHARD_SOFT_LIMIT_SECONDS
    )


def test_runtime_sharder_enforces_safe_minimum_parts(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    output = tmp_path / "runtime"
    matrix = tmp_path / "matrix.json"
    sources.mkdir()
    (sources / "batch_1.txt").write_text(
        "\n".join(f"https://example.com/{index}" for index in range(18)) + "\n",
        encoding="utf-8",
    )

    import sys

    original = sys.argv
    try:
        sys.argv = [
            "shard_sources.py",
            "--sources-dir",
            str(sources),
            "--output-dir",
            str(output),
            "--parts",
            "1",
            "--matrix-output",
            str(matrix),
        ]
        assert shard_sources.main() == 0
    finally:
        sys.argv = original

    generated = sorted(output.glob("batch_1_part_*.txt"))
    assert len(generated) == RUNTIME_SHARD_PARTS
    assert RUNTIME_SHARD_HARD_LIMIT_SECONDS > RUNTIME_SHARD_SOFT_LIMIT_SECONDS
