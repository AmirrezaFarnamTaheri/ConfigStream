# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

from scripts.deduplicate_sources import (
    load_canonical_layout,
    load_canonical_sources,
    rebalance_existing_layout,
    write_source_layout,
)


def test_deduplicator_reads_only_canonical_batches(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    (source_dir / "batch_1.txt").write_text(
        "https://canonical.example/list\n", encoding="utf-8"
    )
    assert load_canonical_sources(source_dir) == {"https://canonical.example/list"}


def test_source_layout_is_deterministic(tmp_path: Path) -> None:
    urls = {
        "https://raw.githubusercontent.com/acme/repo/main/a.txt",
        "https://raw.githubusercontent.com/acme/repo/main/b.txt",
        "https://example.test/list",
    }
    initial = [sorted(urls), [], []]
    batches = rebalance_existing_layout(initial)
    source_dir = tmp_path / "sources"
    write_source_layout(batches, sources_dir=source_dir)

    assert {
        line
        for path in source_dir.glob("batch_*.txt")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    } == urls
    assert rebalance_existing_layout(initial) == batches


def test_deduplicator_normalizes_fragments_and_default_ports(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    (source_dir / "batch_1.txt").write_text(
        "https://Example.com:443/list#first\n", encoding="utf-8"
    )
    (source_dir / "batch_2.txt").write_text(
        "https://example.com/list#second\n", encoding="utf-8"
    )

    layout = load_canonical_layout(source_dir, num_batches=2)
    assert layout == [["https://example.com/list"], []]


def test_minimal_rebalance_moves_only_excess_entries() -> None:
    batches = [
        ["https://a.example/1", "https://b.example/1"],
        ["https://c.example/1", "https://d.example/1"],
        [],
    ]
    balanced = rebalance_existing_layout(batches)
    assert sorted(map(len, balanced)) == [1, 1, 2]
    assert {url for batch in balanced for url in batch} == {
        url for batch in batches for url in batch
    }
    moved = sum(
        len(set(before) - set(after)) for before, after in zip(batches, balanced)
    )
    assert moved == 1
