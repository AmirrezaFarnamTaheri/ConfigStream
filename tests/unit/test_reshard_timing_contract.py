# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import dynamic_reshard
from scripts.shard_sources import (
    TIMING_WEIGHTS_FILENAME,
    _source_set_sha256,
    load_timing_weights,
    partition,
    source_timing_id,
)
from tools.apply_reshard import _validate_timing_weights


def _write_sidecar(
    directory: Path,
    urls: set[str],
    *,
    weights: dict[str, object] | None = None,
    source_set_sha256: str | None = None,
) -> None:
    payload = {
        "schema_version": 1,
        "unit": "deciseconds",
        "default_weight": 130,
        "source_set_sha256": source_set_sha256 or _source_set_sha256(urls),
        "weights": weights or {},
    }
    (directory / TIMING_WEIGHTS_FILENAME).write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_unweighted_partition_remains_generic() -> None:
    values = ["vmess://example", "vless://example", "trojan://example"]

    buckets = partition(values, 2)

    assert sorted(item for bucket in buckets for item in bucket) == sorted(values)
    assert sorted(map(len, buckets)) == [1, 2]


def test_runtime_timing_weights_require_exact_source_set(tmp_path: Path) -> None:
    urls = {"https://a.example/sub", "https://b.example/sub"}
    (tmp_path / "batch_1.txt").write_text(
        "# batch\n" + "\n".join(sorted(urls)) + "\n", encoding="utf-8"
    )
    _write_sidecar(
        tmp_path,
        urls,
        source_set_sha256=_source_set_sha256({"https://a.example/sub"}),
    )

    with pytest.raises(SystemExit, match="source-set mismatch"):
        load_timing_weights(tmp_path)


def test_runtime_timing_weights_reject_unknown_source_ids(tmp_path: Path) -> None:
    urls = {"https://a.example/sub"}
    (tmp_path / "batch_1.txt").write_text(
        "https://a.example/sub\n", encoding="utf-8"
    )
    _write_sidecar(tmp_path, urls, weights={"0" * 64: 50})

    with pytest.raises(SystemExit, match="unknown sources"):
        load_timing_weights(tmp_path)


def test_runtime_timing_weights_accept_exact_subset_of_observed_sources(
    tmp_path: Path,
) -> None:
    urls = {"https://a.example/sub", "https://b.example/sub"}
    (tmp_path / "batch_1.txt").write_text(
        "\n".join(sorted(urls)) + "\n", encoding="utf-8"
    )
    source_id = source_timing_id("https://a.example/sub")
    _write_sidecar(tmp_path, urls, weights={source_id: 42})

    weights, default_weight = load_timing_weights(tmp_path)

    assert weights == {source_id: 42}
    assert default_weight == 130
    _validate_timing_weights(tmp_path, urls)


def test_operator_validation_rejects_non_integer_weight(tmp_path: Path) -> None:
    urls = {"https://a.example/sub"}
    source_id = source_timing_id("https://a.example/sub")
    _write_sidecar(tmp_path, urls, weights={source_id: True})

    with pytest.raises(SystemExit, match="invalid source weight"):
        _validate_timing_weights(tmp_path, urls)


def test_source_timing_id_uses_canonical_fetch_identity() -> None:
    assert source_timing_id("HTTPS://Example.COM:443/sub#label") == source_timing_id(
        "https://example.com/sub"
    )


def test_reshard_publication_keeps_old_layout_when_timing_stage_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    original = sources_dir / "batch_1.txt"
    original.write_text("https://old.example/sub\n", encoding="utf-8")
    monkeypatch.setattr(dynamic_reshard, "SOURCES_DIR", sources_dir)

    def fail_timing_write(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated timing sidecar failure")

    monkeypatch.setattr(dynamic_reshard, "_write_timing_weights", fail_timing_write)

    with pytest.raises(OSError, match="simulated timing sidecar failure"):
        dynamic_reshard._publish_reshard_layout(
            [["https://new.example/sub"]],
            [130],
            {"https://new.example/sub"},
            {},
            130,
        )

    assert original.read_text(encoding="utf-8") == "https://old.example/sub\n"
    assert not (sources_dir / TIMING_WEIGHTS_FILENAME).exists()
    assert not list(sources_dir.glob("*.reshard-new"))
    assert not list(sources_dir.glob("*.reshard-backup"))
