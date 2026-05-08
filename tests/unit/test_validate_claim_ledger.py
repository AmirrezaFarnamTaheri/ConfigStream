# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for claim ledger validation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import validate_claim_ledger


def _valid_ledger() -> dict[str, object]:
    return {
        "claims": [
            {
                "id": "claim.test.complete",
                "claim": "A complete claim has proof.",
                "source": "STATUS.md",
                "product_area": "tests",
                "status": "complete",
                "owner": "scripts/example.py",
                "tests": ["tests/unit/test_example.py"],
                "frontend_surface": None,
                "output_artifact": None,
                "docs": ["STATUS.md"],
                "changelog": "CHANGELOG.md",
                "cleanup_decision": "Keep guarded.",
            }
        ]
    }


def _write_ledger(tmp_path: Path, ledger: dict[str, object]) -> Path:
    path = tmp_path / "claim_ledger.json"
    path.write_text(json.dumps(ledger), encoding="utf-8")
    return path


def test_validate_claim_ledger_accepts_complete_claim(tmp_path: Path) -> None:
    path = _write_ledger(tmp_path, _valid_ledger())

    assert validate_claim_ledger.validate_claim_ledger(path) == []


def test_validate_claim_ledger_rejects_duplicate_ids(tmp_path: Path) -> None:
    ledger = _valid_ledger()
    ledger["claims"] = [ledger["claims"][0], dict(ledger["claims"][0])]  # type: ignore[index]
    path = _write_ledger(tmp_path, ledger)

    errors = validate_claim_ledger.validate_claim_ledger(path)

    assert "duplicate claim id: claim.test.complete" in errors


def test_validate_claim_ledger_rejects_complete_claim_without_tests(
    tmp_path: Path,
) -> None:
    ledger = _valid_ledger()
    claim = ledger["claims"][0]  # type: ignore[index]
    claim["tests"] = []  # type: ignore[index]
    path = _write_ledger(tmp_path, ledger)

    errors = validate_claim_ledger.validate_claim_ledger(path)

    assert any("complete claim must list proving tests" in error for error in errors)


def test_validate_claim_ledger_rejects_invalid_status(tmp_path: Path) -> None:
    ledger = _valid_ledger()
    claim = ledger["claims"][0]  # type: ignore[index]
    claim["status"] = "aspirational"  # type: ignore[index]
    path = _write_ledger(tmp_path, ledger)

    errors = validate_claim_ledger.validate_claim_ledger(path)

    assert any("status is invalid" in error for error in errors)
