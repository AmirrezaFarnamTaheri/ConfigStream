# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

from scripts import prepare_public_candidate


def test_prepare_public_candidate_preserves_previous_on_failed_swap(
    tmp_path: Path, monkeypatch
) -> None:
    merged = tmp_path / "merged"
    frontend = tmp_path / "frontend"
    destination = tmp_path / "output"
    merged.mkdir()
    frontend.mkdir()
    (merged / "metadata.json").write_text("{}", encoding="utf-8")
    (frontend / "index.html").write_text("new", encoding="utf-8")
    destination.mkdir()
    (destination / "old.txt").write_text("old", encoding="utf-8")

    original_replace = Path.replace
    replace_count = 0

    def fail_second_replace(self: Path, target: Path) -> Path:
        nonlocal replace_count
        replace_count += 1
        if replace_count == 2:
            raise OSError("simulated swap failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_second_replace)
    try:
        prepare_public_candidate.prepare(merged, frontend, destination, tmp_path)
    except OSError:
        pass
    else:
        raise AssertionError("swap should fail")

    assert (destination / "old.txt").read_text(encoding="utf-8") == "old"
