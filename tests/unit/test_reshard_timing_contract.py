# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.shard_sources import (
    TIMING_WEIGHTS_FILENAME,
    load_timing_weights,
    source_timing_id,
)
from tools.apply_reshard import _validate_timing_weights


def _source_set_sha256(urls: set[str]) -> str:
    return hashlib.sha256(
        ("\n".join(sorted(urls)) + "\n").encode("utf-8")
    ).hexdigest()


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
