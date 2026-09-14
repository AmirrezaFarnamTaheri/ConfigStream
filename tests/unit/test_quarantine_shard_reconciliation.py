# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

from scripts.aggregate_shard_health import expected_from_sources
from scripts.shard_sources import (
    MIN_RUNTIME_SHARD_PARTS,
    active_source_lines,
    load_quarantined_sources,
    partition,
)


def test_expected_shards_exclude_quarantine_only_batch(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    quarantined_url = "https://quarantined.example/sub"
    active_urls = [
        "https://active-one.example/sub",
        "https://active-two.example/sub",
    ]
    (sources / "batch_1.txt").write_text(quarantined_url + "\n", encoding="utf-8")
    (sources / "batch_2.txt").write_text(
        "\n".join(active_urls) + "\n", encoding="utf-8"
    )
    (sources / "quarantine.txt").write_text(
        "# disabled by operator\n" + quarantined_url + "\n", encoding="utf-8"
    )

    quarantined = load_quarantined_sources(sources)
    active_expected = sum(
        bool(bucket)
        for bucket in partition(
            active_source_lines(sources / "batch_2.txt", quarantined), MIN_RUNTIME_SHARD_PARTS
        )
    )

    assert active_source_lines(sources / "batch_1.txt", quarantined) == []
    assert expected_from_sources(sources, parts=4) == active_expected


def test_expected_shards_are_zero_when_every_source_is_quarantined(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    url = "https://quarantined.example/sub"
    (sources / "batch_1.txt").write_text(url + "\n", encoding="utf-8")
    (sources / "quarantine.txt").write_text(url + "\n", encoding="utf-8")

    assert expected_from_sources(sources, parts=4) == 0


def test_runtime_cost_quarantine_is_applied_without_mutating_admission(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    url = "https://expensive.example/huge-list"
    (sources / "batch_1.txt").write_text(url + "\n", encoding="utf-8")
    (sources / "runtime_quarantine.txt").write_text(
        "# production cost quarantine\n" + url + "\n", encoding="utf-8"
    )

    quarantined = load_quarantined_sources(sources)

    assert quarantined == {url}
    assert active_source_lines(sources / "batch_1.txt", quarantined) == []
    assert expected_from_sources(sources, parts=6) == 0
