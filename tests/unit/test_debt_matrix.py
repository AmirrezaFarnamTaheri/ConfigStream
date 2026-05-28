# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for debt matrix generation and validation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import generate_debt_matrix, validate_debt_matrix


def test_generate_debt_matrix_uses_repo_relative_paths(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path
    source = root / "src" / "configstream"
    source.mkdir(parents=True)
    file_path = source / "module.py"
    file_path.write_text("# TODO: tighten behavior\n", encoding="utf-8")

    monkeypatch.setattr(generate_debt_matrix, "ROOT", root)

    entries = generate_debt_matrix._scan_files([file_path])

    assert entries == [
        {
            "path": "src/configstream/module.py",
            "line": 1,
            "marker": "TODO",
            "category": "production",
            "priority": "P0 - Critical",
            "text": "# TODO: tighten behavior",
        }
    ]


def test_generate_debt_matrix_excludes_generated_outputs() -> None:
    assert not generate_debt_matrix._is_scannable("docs/DEBT_MATRIX.md")
    assert not generate_debt_matrix._is_scannable("docs/debt_matrix.json")
    assert not generate_debt_matrix._is_scannable(
        "docs/history/source-of-truth/ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.full.md"
    )
    assert not generate_debt_matrix._is_scannable(
        "docs/history/source-of-truth/Main SOURCE OF TRUTH - Ammendment.md"
    )
    assert not generate_debt_matrix._is_scannable(
        "docs/history/source-of-truth/Main SOURCE OF TRUTH - PART 2.md"
    )
    assert not generate_debt_matrix._is_scannable(
        "docs/history/source-of-truth/Main SOURCE OF TRUTH - PART 3.md"
    )


def test_generate_debt_matrix_classifies_test_mocks() -> None:
    assert generate_debt_matrix._classify_path("tests/unit/test_example.py") == "test"
    assert (
        generate_debt_matrix._classify_path("src/configstream/server.py")
        == "production"
    )


def test_validate_debt_matrix_rejects_absolute_paths(
    tmp_path: Path, monkeypatch
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "debt_matrix.json").write_text(
        json.dumps(
            {
                "summary": {"categories": {"production": 1}},
                "entries": [
                    {
                        "path": "D:/GitHub/ConfigStream/src/example.py",
                        "line": 1,
                        "marker": "TODO",
                        "category": "production",
                        "text": "TODO",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (docs / "DEBT_MATRIX.md").write_text("## Categories\n", encoding="utf-8")
    monkeypatch.setattr(validate_debt_matrix, "ROOT", tmp_path)
    monkeypatch.setattr(validate_debt_matrix, "DEBT_JSON", docs / "debt_matrix.json")
    monkeypatch.setattr(validate_debt_matrix, "DEBT_MD", docs / "DEBT_MATRIX.md")

    errors = validate_debt_matrix.validate_debt_matrix()

    assert any("absolute path" in error for error in errors)


def test_validate_debt_matrix_accepts_portable_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "debt_matrix.json").write_text(
        json.dumps(
            {
                "summary": {"categories": {"production": 1}},
                "entries": [
                    {
                        "path": "src/example.py",
                        "line": 1,
                        "marker": "TODO",
                        "category": "production",
                        "text": "TODO",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (docs / "DEBT_MATRIX.md").write_text(
        "## Categories\n\n| `src/example.py` | 1 | TODO |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_debt_matrix, "ROOT", tmp_path)
    monkeypatch.setattr(validate_debt_matrix, "DEBT_JSON", docs / "debt_matrix.json")
    monkeypatch.setattr(validate_debt_matrix, "DEBT_MD", docs / "DEBT_MATRIX.md")

    assert validate_debt_matrix.validate_debt_matrix() == []
