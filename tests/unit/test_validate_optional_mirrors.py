# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for optional mirror documentation guardrails."""

from __future__ import annotations

from pathlib import Path

from scripts import validate_optional_mirrors


def _write_docs(tmp_path: Path, text: str) -> list[Path]:
    paths = [
        tmp_path / "docs/wiki/project/01-introduction.md",
        tmp_path / "docs/wiki/project/02-architecture.md",
        tmp_path / "docs/wiki/project/05-devops.md",
        tmp_path / "docs/wiki/project/Configuration.md",
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return paths


def test_validate_optional_mirrors_accepts_optional_secret_gated_docs(
    tmp_path: Path, monkeypatch
) -> None:
    paths = _write_docs(
        tmp_path,
        "GitHub Pages is the core zero-budget publication target.\n"
        "External mirrors are optional and secret-gated.\n",
    )
    monkeypatch.setattr(validate_optional_mirrors, "DOC_FILES", paths)

    assert validate_optional_mirrors.validate_optional_mirrors() == []


def test_validate_optional_mirrors_rejects_core_mirror_claim(
    tmp_path: Path, monkeypatch
) -> None:
    paths = _write_docs(
        tmp_path,
        "GitHub Pages is the core zero-budget publication target.\n"
        "External mirrors are optional and secret-gated.\n"
        "we have mirrors on GitLab, Hugging Face, and IPFS\n",
    )
    monkeypatch.setattr(validate_optional_mirrors, "DOC_FILES", paths)

    errors = validate_optional_mirrors.validate_optional_mirrors()

    assert errors == [
        "optional mirror docs contain core-capability claim: "
        "we have mirrors on GitLab, Hugging Face, and IPFS"
    ]


def test_validate_optional_mirrors_requires_optional_language(
    tmp_path: Path, monkeypatch
) -> None:
    paths = _write_docs(tmp_path, "External mirrors are optional.\n")
    monkeypatch.setattr(validate_optional_mirrors, "DOC_FILES", paths)

    errors = validate_optional_mirrors.validate_optional_mirrors()

    assert any("GitHub Pages is the core" in error for error in errors)
    assert any("secret-gated" in error for error in errors)
