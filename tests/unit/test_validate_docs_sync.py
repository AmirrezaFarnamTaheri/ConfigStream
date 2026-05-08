# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for encyclopedia documentation mirror validation."""

from __future__ import annotations

from pathlib import Path

from scripts import validate_docs_sync


def _patch_roots(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    canonical = tmp_path / "docs" / "wiki" / "encyclopedia"
    mirror = tmp_path / "docs" / "encyclopedia"
    canonical.mkdir(parents=True)
    mirror.mkdir(parents=True)
    monkeypatch.setattr(validate_docs_sync, "CANONICAL", canonical)
    monkeypatch.setattr(validate_docs_sync, "MIRROR", mirror)
    return canonical, mirror


def test_validate_docs_sync_accepts_identical_mirror(
    tmp_path: Path, monkeypatch
) -> None:
    canonical, mirror = _patch_roots(tmp_path, monkeypatch)
    (canonical / "protocols").mkdir()
    (mirror / "protocols").mkdir()
    (canonical / "protocols" / "vless.md").write_text("same\n", encoding="utf-8")
    (mirror / "protocols" / "vless.md").write_text("same\n", encoding="utf-8")

    assert validate_docs_sync.validate_docs_sync() == []


def test_validate_docs_sync_rejects_drift(tmp_path: Path, monkeypatch) -> None:
    canonical, mirror = _patch_roots(tmp_path, monkeypatch)
    (canonical / "glossary").mkdir()
    (mirror / "glossary").mkdir()
    (canonical / "glossary" / "networking_terms.md").write_text(
        "canonical\n", encoding="utf-8"
    )
    (mirror / "glossary" / "networking_terms.md").write_text(
        "stale\n", encoding="utf-8"
    )

    errors = validate_docs_sync.validate_docs_sync()

    assert errors == ["encyclopedia mirror drift: glossary/networking_terms.md"]


def test_validate_docs_sync_rejects_extra_mirror_files(
    tmp_path: Path, monkeypatch
) -> None:
    canonical, mirror = _patch_roots(tmp_path, monkeypatch)
    (mirror / "extra.md").write_text("unmanaged\n", encoding="utf-8")

    errors = validate_docs_sync.validate_docs_sync()

    assert errors == ["docs/encyclopedia has unmanaged extra file: extra.md"]
