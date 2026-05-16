# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for module ownership map validation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import validate_module_ownership


def _write_json(path: Path, data: dict[str, object]) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _valid_map() -> dict[str, object]:
    return {
        "modules": [
            {
                "path": "STATUS.md",
                "domain": "test-domain",
                "owner": "tests",
                "public_apis": ["Example"],
                "internal_only_apis": [],
                "disallowed_duplicates": [],
                "replacement_for_removed_modules": [],
                "tests": ["tests/unit/test_validate_module_ownership.py"],
                "docs": ["STATUS.md"],
            }
        ],
        "removed_modules": [
            {
                "path": "missing_removed_module.py",
                "import_names": ["configstream.removed_example"],
                "replacement": "STATUS.md",
            }
        ],
    }


def test_validate_module_ownership_accepts_current_repo() -> None:
    assert validate_module_ownership.validate_module_ownership() == []


def test_validate_module_ownership_accepts_valid_map(
    tmp_path: Path, monkeypatch
) -> None:
    ownership_map = _write_json(tmp_path / "module_ownership.json", _valid_map())
    monkeypatch.setattr(validate_module_ownership, "ROOT", Path.cwd())

    assert validate_module_ownership.validate_module_ownership(ownership_map) == []


def test_validate_module_ownership_rejects_missing_proof_path(
    tmp_path: Path, monkeypatch
) -> None:
    data = _valid_map()
    module = data["modules"][0]  # type: ignore[index]
    module["tests"] = ["tests/unit/missing_test.py"]  # type: ignore[index]
    ownership_map = _write_json(tmp_path / "module_ownership.json", data)
    monkeypatch.setattr(validate_module_ownership, "ROOT", Path.cwd())

    errors = validate_module_ownership.validate_module_ownership(ownership_map)

    assert any("tests/unit/missing_test.py" in error for error in errors)


def test_validate_module_ownership_rejects_recreated_removed_path(
    tmp_path: Path, monkeypatch
) -> None:
    data = _valid_map()
    removed = data["removed_modules"][0]  # type: ignore[index]
    removed["path"] = "STATUS.md"  # type: ignore[index]
    ownership_map = _write_json(tmp_path / "module_ownership.json", data)
    monkeypatch.setattr(validate_module_ownership, "ROOT", Path.cwd())

    errors = validate_module_ownership.validate_module_ownership(ownership_map)

    assert any("has been recreated: STATUS.md" in error for error in errors)


def test_validate_module_ownership_rejects_removed_import(
    tmp_path: Path, monkeypatch
) -> None:
    source_root = tmp_path / "src"
    source_root.mkdir()
    (source_root / "example.py").write_text(
        "from configstream.removed_example import legacy\n",
        encoding="utf-8",
    )
    (tmp_path / "STATUS.md").write_text("status", encoding="utf-8")
    tests_dir = tmp_path / "tests" / "unit"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_validate_module_ownership.py").write_text(
        "def test_placeholder(): pass\n",
        encoding="utf-8",
    )
    ownership_map = _write_json(tmp_path / "module_ownership.json", _valid_map())
    monkeypatch.setattr(validate_module_ownership, "ROOT", tmp_path)

    errors = validate_module_ownership.validate_module_ownership(ownership_map)

    assert any(
        "imports removed module configstream.removed_example" in error
        for error in errors
    )
