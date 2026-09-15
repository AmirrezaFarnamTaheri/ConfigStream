# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

from scripts.aggregate_shard_health import expected_from_sources
from scripts.source_shard_policy import RUNTIME_SHARD_PARTS


def test_aggregate_uses_same_runtime_shard_floor_as_matrix(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    urls = [f"https://source-{index}.example/sub" for index in range(12)]
    (sources / "batch_1.txt").write_text(
        "\n".join(urls) + "\n", encoding="utf-8"
    )

    assert expected_from_sources(sources, RUNTIME_SHARD_PARTS - 3) == RUNTIME_SHARD_PARTS
    assert expected_from_sources(sources, RUNTIME_SHARD_PARTS + 1) == (
        RUNTIME_SHARD_PARTS + 1
    )
