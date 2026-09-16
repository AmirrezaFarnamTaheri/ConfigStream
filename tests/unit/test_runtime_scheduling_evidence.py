# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from scripts.shard_sources import (
    RUNTIME_QUARANTINE_FILENAME,
    TIMING_WEIGHTS_FILENAME,
    _source_set_sha256,
    load_quarantined_sources,
    load_timing_weights,
    partition,
    runtime_shard_parts,
    runtime_source_lines,
    source_timing_id,
)
from scripts.source_shard_policy import RUNTIME_SHARD_PARTS


def test_runtime_cost_quarantine_is_combined_with_operator_quarantine(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    legacy = "https://legacy.example/sub"
    expensive = "https://expensive.example/sub"
    healthy = "https://healthy.example/sub"
    batch = sources / "batch_1.txt"
    batch.write_text(f"{legacy}\n{expensive}\n{healthy}\n", encoding="utf-8")
    (sources / "quarantine.txt").write_text(legacy + "\n", encoding="utf-8")
    (sources / RUNTIME_QUARANTINE_FILENAME).write_text(
        "# measured runtime-cost quarantine\n" + expensive + "\n", encoding="utf-8"
    )

    quarantined = load_quarantined_sources(sources)

    assert quarantined == {legacy, expensive}
    assert runtime_source_lines(batch, quarantined) == [healthy]


def test_runtime_timing_weights_accept_compact_vector_schema(tmp_path: Path) -> None:
    urls = {"https://a.example/sub", "https://b.example/sub"}
    ordered = sorted(urls)
    (tmp_path / "batch_1.txt").write_text("\n".join(ordered) + "\n", encoding="utf-8")
    payload = {
        "schema_version": 2,
        "unit": "deciseconds",
        "default_weight": 130,
        "source_set_sha256": _source_set_sha256(urls),
        "weights_by_sorted_source": [41, 73],
    }
    (tmp_path / TIMING_WEIGHTS_FILENAME).write_text(
        json.dumps(payload), encoding="utf-8"
    )

    weights, default_weight = load_timing_weights(tmp_path)

    assert weights == {
        source_timing_id(ordered[0]): 41,
        source_timing_id(ordered[1]): 73,
    }
    assert default_weight == 130


def test_runtime_sources_exclude_provably_non_feed_locator_shapes(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    eligible = [
        "https://raw.githubusercontent.com/example/repo/main/sub.txt",
        "https://github.com/example/repo/raw/main/sub.txt",
        "https://example.com/subscription",
        "https://gist.github.com/example/0123456789abcdef/raw/config.txt",
    ]
    ineligible = [
        "http://example.com/insecure",
        "https://freevpnspy.raw.githubusercontent.com/2024/08/config.yaml",
        "https://t.me/example_channel",
        "https://check.torproject.org/torbulkexitlist",
        "https://gist.github.com/example",
        "https://github.com/example/repo",
        "https://github.com/example",
        "https://github.com/example/repo/blob/main/sub.txt",
    ]
    batch = sources / "batch_1.txt"
    batch.write_text("\n".join([*eligible, *ineligible]) + "\n", encoding="utf-8")

    assert runtime_source_lines(batch, set()) == eligible


def test_runtime_shard_parts_enforces_shared_policy_floor() -> None:
    assert runtime_shard_parts(RUNTIME_SHARD_PARTS - 3) == RUNTIME_SHARD_PARTS
    assert runtime_shard_parts(RUNTIME_SHARD_PARTS + 2) == RUNTIME_SHARD_PARTS + 2


def test_partition_keeps_explicit_historical_part_counts() -> None:
    urls = [f"https://source-{index}.example/sub" for index in range(12)]

    buckets = partition(urls, RUNTIME_SHARD_PARTS - 3)

    assert len(buckets) == RUNTIME_SHARD_PARTS - 3
    assert sorted(item for bucket in buckets for item in bucket) == sorted(urls)
