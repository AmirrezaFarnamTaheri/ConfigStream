# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for capability registry validation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import validate_capability_registry


def _write_json(path: Path, data: dict[str, object]) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _valid_registry() -> dict[str, object]:
    return {
        "capabilities": [
            {
                "id": "cap.test.stable",
                "title": "Stable test capability",
                "status": "stable",
                "product_area": "tests",
                "owner": "STATUS.md",
                "implementation": ["STATUS.md"],
                "claim_ids": ["claim.test.complete"],
                "tests": ["tests/unit/test_validate_capability_registry.py"],
                "docs": ["STATUS.md"],
                "outputs": [],
                "limitations": ["Repository-local proof only."],
                "cleanup_decision": "Keep guarded.",
            }
        ]
    }


def _claim_ledger() -> dict[str, object]:
    return {
        "claims": [
            {
                "id": "claim.test.complete",
                "status": "complete",
            }
        ]
    }


def test_validate_capability_registry_accepts_current_repo() -> None:
    assert validate_capability_registry.validate_capability_registry() == []


def test_validate_capability_registry_accepts_stable_capability(
    tmp_path: Path, monkeypatch
) -> None:
    registry = _write_json(tmp_path / "capability_registry.json", _valid_registry())
    ledger = _write_json(tmp_path / "claim_ledger.json", _claim_ledger())
    monkeypatch.setattr(validate_capability_registry, "ROOT", Path.cwd())
    monkeypatch.setattr(validate_capability_registry, "CLAIM_LEDGER_PATH", ledger)

    assert validate_capability_registry.validate_capability_registry(registry) == []


def test_validate_capability_registry_rejects_duplicate_ids(
    tmp_path: Path, monkeypatch
) -> None:
    data = _valid_registry()
    data["capabilities"] = [
        data["capabilities"][0],  # type: ignore[index]
        dict(data["capabilities"][0]),  # type: ignore[index]
    ]
    registry = _write_json(tmp_path / "capability_registry.json", data)
    ledger = _write_json(tmp_path / "claim_ledger.json", _claim_ledger())
    monkeypatch.setattr(validate_capability_registry, "ROOT", Path.cwd())
    monkeypatch.setattr(validate_capability_registry, "CLAIM_LEDGER_PATH", ledger)

    errors = validate_capability_registry.validate_capability_registry(registry)

    assert "duplicate capability id: cap.test.stable" in errors


def test_validate_capability_registry_rejects_stable_without_complete_claim(
    tmp_path: Path, monkeypatch
) -> None:
    registry = _write_json(tmp_path / "capability_registry.json", _valid_registry())
    ledger = _write_json(tmp_path / "claim_ledger.json", {"claims": []})
    monkeypatch.setattr(validate_capability_registry, "ROOT", Path.cwd())
    monkeypatch.setattr(validate_capability_registry, "CLAIM_LEDGER_PATH", ledger)

    errors = validate_capability_registry.validate_capability_registry(registry)

    assert any("non-complete claim" in error for error in errors)


def test_validate_capability_registry_rejects_missing_stable_paths(
    tmp_path: Path, monkeypatch
) -> None:
    data = _valid_registry()
    capability = data["capabilities"][0]  # type: ignore[index]
    capability["implementation"] = ["missing-file.py"]  # type: ignore[index]
    registry = _write_json(tmp_path / "capability_registry.json", data)
    ledger = _write_json(tmp_path / "claim_ledger.json", _claim_ledger())
    monkeypatch.setattr(validate_capability_registry, "ROOT", Path.cwd())
    monkeypatch.setattr(validate_capability_registry, "CLAIM_LEDGER_PATH", ledger)

    errors = validate_capability_registry.validate_capability_registry(registry)

    assert any("path is missing: missing-file.py" in error for error in errors)
