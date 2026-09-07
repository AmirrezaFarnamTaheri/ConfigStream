# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression coverage for the local reshard helper's security contract."""

from __future__ import annotations

import importlib.util
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


def test_apply_swaps_layout_and_preserves_unrelated_sources_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = tmp_path / "sources"
    recommendation = tmp_path / "recommendation"
    sources.mkdir()
    recommendation.mkdir()
    (sources / "batch_1.txt").write_text("old\n", encoding="utf-8")
    (sources / "batch_2.txt").write_text("stale\n", encoding="utf-8")
    (sources / "quarantine.txt").write_text("keep\n", encoding="utf-8")
    (sources / apply_reshard.TIMING_WEIGHTS_FILENAME).write_text(
        "old-sidecar\n", encoding="utf-8"
    )
    (recommendation / "batch_1.txt").write_text("new\n", encoding="utf-8")
    (recommendation / apply_reshard.TIMING_WEIGHTS_FILENAME).write_text(
        "new-sidecar\n", encoding="utf-8"
    )
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

    assert sources.is_dir()
    assert (sources / "batch_1.txt").read_text(encoding="utf-8") == "old\n"
    assert (sources / "quarantine.txt").read_text(encoding="utf-8") == "keep\n"
    assert (sources / apply_reshard.TIMING_WEIGHTS_FILENAME).read_text(
        encoding="utf-8"
    ) == "old-sidecar\n"
