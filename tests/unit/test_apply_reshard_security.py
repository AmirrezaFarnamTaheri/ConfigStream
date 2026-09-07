# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression coverage for the local reshard helper's security contract."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "apply_reshard.py"
SPEC = importlib.util.spec_from_file_location("apply_reshard", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
apply_reshard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(apply_reshard)


def test_resolve_executable_returns_absolute_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(apply_reshard.shutil, "which", lambda name: f"/usr/bin/{name}")

    assert apply_reshard._resolve_executable("git") == "/usr/bin/git"


def test_resolve_executable_fails_closed_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(apply_reshard.shutil, "which", lambda _name: None)

    with pytest.raises(SystemExit, match="gh CLI not found on PATH"):
        apply_reshard._resolve_executable("gh")


def test_source_timing_identity_uses_canonical_fetch_locator() -> None:
    first = "https://example.com/subscription?token=abc#label-one"
    second = "https://example.com/subscription?token=abc#label-two"

    assert apply_reshard._source_timing_id(first) == apply_reshard._source_timing_id(
        second
    )
    assert apply_reshard._source_set_sha256({first}) == apply_reshard._source_set_sha256(
        {second}
    )


def _write_sidecar(directory: Path, urls: set[str], *, weight: int = 10) -> None:
    weights = {apply_reshard._source_timing_id(url): weight for url in urls}
    payload = {
        "schema_version": 1,
        "unit": "deciseconds",
        "source_set_sha256": apply_reshard._source_set_sha256(urls),
        "default_weight": weight,
        "weights": weights,
    }
    (directory / apply_reshard.TIMING_WEIGHTS_FILENAME).write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _write_layout_fixture(sources: Path, recommendation: Path) -> None:
    sources.mkdir()
    recommendation.mkdir()
    (sources / "batch_1.txt").write_text("old\n", encoding="utf-8")
    (sources / "quarantine.txt").write_text("keep\n", encoding="utf-8")
    (sources / apply_reshard.TIMING_WEIGHTS_FILENAME).write_text(
        "old-sidecar\n", encoding="utf-8"
    )
    (recommendation / "batch_1.txt").write_text("new\n", encoding="utf-8")
    (recommendation / apply_reshard.TIMING_WEIGHTS_FILENAME).write_text(
        "new-sidecar\n", encoding="utf-8"
    )


def _assert_old_layout_restored(sources: Path) -> None:
    assert sources.is_dir()
    assert (sources / "batch_1.txt").read_text(encoding="utf-8") == "old\n"
    assert (sources / "quarantine.txt").read_text(encoding="utf-8") == "keep\n"
    assert (sources / apply_reshard.TIMING_WEIGHTS_FILENAME).read_text(
        encoding="utf-8"
    ) == "old-sidecar\n"


def test_validate_rejects_duplicate_canonical_fetch_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = tmp_path / "sources"
    recommendation = tmp_path / "recommendation"
    sources.mkdir()
    recommendation.mkdir()
    url = "https://example.com/subscription?token=abc"
    (sources / "batch_1.txt").write_text(f"{url}\n", encoding="utf-8")
    (recommendation / "batch_1.txt").write_text(
        f"# Est. Fetch Time: 1.0s\n{url}\n", encoding="utf-8"
    )
    (recommendation / "batch_2.txt").write_text(
        f"# Est. Fetch Time: 1.0s\n{url}#duplicate-label\n", encoding="utf-8"
    )
    _write_sidecar(recommendation, {url})
    monkeypatch.setattr(apply_reshard, "SOURCES_DIR", sources)

    with pytest.raises(SystemExit, match="repeats canonical source fetch identity"):
        apply_reshard._validate(recommendation)


def test_validate_recomputes_batch_estimate_from_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = tmp_path / "sources"
    recommendation = tmp_path / "recommendation"
    sources.mkdir()
    recommendation.mkdir()
    url = "https://example.com/subscription"
    (sources / "batch_1.txt").write_text(f"{url}\n", encoding="utf-8")
    (recommendation / "batch_1.txt").write_text(
        f"# Est. Fetch Time: 0.1s\n{url}\n", encoding="utf-8"
    )
    _write_sidecar(recommendation, {url}, weight=20)
    monkeypatch.setattr(apply_reshard, "SOURCES_DIR", sources)

    with pytest.raises(SystemExit, match="does not match timing sidecar"):
        apply_reshard._validate(recommendation)


def test_apply_swaps_layout_and_preserves_unrelated_sources_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = tmp_path / "sources"
    recommendation = tmp_path / "recommendation"
    _write_layout_fixture(sources, recommendation)
    (sources / "batch_2.txt").write_text("stale\n", encoding="utf-8")
    monkeypatch.setattr(apply_reshard, "SOURCES_DIR", sources)

    assert apply_reshard._apply(recommendation) is True
    assert (sources / "batch_1.txt").read_text(encoding="utf-8") == "new\n"
    assert not (sources / "batch_2.txt").exists()
    assert (sources / "quarantine.txt").read_text(encoding="utf-8") == "keep\n"
    assert (sources / apply_reshard.TIMING_WEIGHTS_FILENAME).read_text(
        encoding="utf-8"
    ) == "new-sidecar\n"


def test_apply_rolls_back_when_directory_handoff_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = tmp_path / "sources"
    recommendation = tmp_path / "recommendation"
    _write_layout_fixture(sources, recommendation)
    monkeypatch.setattr(apply_reshard, "SOURCES_DIR", sources)

    real_replace = apply_reshard.os.replace
    calls = 0

    def fail_second_replace(src: Path, dst: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected publication failure")
        real_replace(src, dst)

    monkeypatch.setattr(apply_reshard.os, "replace", fail_second_replace)

    with pytest.raises(OSError, match="injected publication failure"):
        apply_reshard._apply(recommendation)

    _assert_old_layout_restored(sources)


def test_apply_rolls_back_when_publication_is_interrupted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = tmp_path / "sources"
    recommendation = tmp_path / "recommendation"
    _write_layout_fixture(sources, recommendation)
    monkeypatch.setattr(apply_reshard, "SOURCES_DIR", sources)

    real_replace = apply_reshard.os.replace
    calls = 0

    def interrupt_second_replace(src: Path, dst: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        real_replace(src, dst)

    monkeypatch.setattr(apply_reshard.os, "replace", interrupt_second_replace)

    with pytest.raises(KeyboardInterrupt):
        apply_reshard._apply(recommendation)

    _assert_old_layout_restored(sources)
