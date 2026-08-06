# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for debt matrix generation and validation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import generate_debt_matrix


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
    assert generate_debt_matrix._is_scannable("docs/current_policy.md")


def test_generate_debt_matrix_classifies_test_mocks() -> None:
    assert generate_debt_matrix._classify_path("tests/unit/test_example.py") == "test"
    assert (
        generate_debt_matrix._classify_path("src/configstream/server.py")
        == "production"
    )


def test_debt_matrix_check_rejects_absolute_paths(
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
    monkeypatch.setattr(generate_debt_matrix, "ROOT", tmp_path)
    monkeypatch.setattr(generate_debt_matrix, "OUT_JSON", docs / "debt_matrix.json")
    monkeypatch.setattr(generate_debt_matrix, "OUT_MD", docs / "DEBT_MATRIX.md")

    errors = generate_debt_matrix.validate_artifacts()

    assert any("absolute path" in error for error in errors)


def test_debt_matrix_check_accepts_portable_artifacts(
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
    monkeypatch.setattr(generate_debt_matrix, "ROOT", tmp_path)
    monkeypatch.setattr(generate_debt_matrix, "OUT_JSON", docs / "debt_matrix.json")
    monkeypatch.setattr(generate_debt_matrix, "OUT_MD", docs / "DEBT_MATRIX.md")

    assert generate_debt_matrix.validate_artifacts() == []


def test_structural_debt_scan_finds_broad_exception_and_large_function(tmp_path, monkeypatch):
    root = tmp_path
    source = root / "src" / "configstream"
    source.mkdir(parents=True)
    body = "\n".join("    value += 1" for _ in range(300))
    path = source / "large.py"
    path.write_text(
        "def large():\n    value = 0\n"
        + body
        + "\n    try:\n        return value\n    except Exception:\n        return 0\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(generate_debt_matrix, "ROOT", root)
    entries = generate_debt_matrix._scan_structural_debt([path])
    markers = {entry["marker"] for entry in entries}
    assert markers == {"BROAD_EXCEPTION", "LARGE_FUNCTION"}


def test_debt_matrix_outputs_are_reproducible(tmp_path: Path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    out_json = docs / "debt_matrix.json"
    out_md = docs / "DEBT_MATRIX.md"
    monkeypatch.setattr(generate_debt_matrix, "OUT_JSON", out_json)
    monkeypatch.setattr(generate_debt_matrix, "OUT_MD", out_md)
    entries = [
        {
            "path": "src/example.py",
            "line": 1,
            "marker": "TODO",
            "category": "production",
            "priority": "P0 - Critical",
            "text": "TODO: replace placeholder",
        }
    ]

    generate_debt_matrix._write_outputs(entries)
    first_json = out_json.read_bytes()
    first_markdown = out_md.read_bytes()
    generate_debt_matrix._write_outputs(entries)

    assert out_json.read_bytes() == first_json
    assert out_md.read_bytes() == first_markdown
    assert json.loads(first_json)["generated_from"] == "current tracked tree"
