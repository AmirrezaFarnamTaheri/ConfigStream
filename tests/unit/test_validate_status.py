# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for machine-readable release-state guardrails."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.release_state import render_status
from scripts import validate_status


def _readiness(**overrides):
    data = {
        "schema_version": "2",
        "project_version": "3.1.0",
        "evaluated_at": "2026-08-01T00:00:00+00:00",
        "verdict": "CONDITIONAL",
        "release_gate": "external_verification_required",
        "production_ready": False,
        "required_gates": {
            "local_release_contract": {"status": "passing", "evidence": ["local.json"]},
            "blocking_ci_green": {"status": "unverified", "evidence": []},
            "live_pages_digest_and_smoke_verified": {"status": "unverified", "evidence": []},
        },
        "release_invariant": "A release is prohibited unless every required gate is passing.",
        "evidence_boundary": "Local verification does not prove remote CI or live deployment state.",
    }
    data.update(overrides)
    return data


def _write_repo(root: Path, readiness: dict, *, classifier: str = "4 - Beta") -> None:
    (root / "docs").mkdir()
    (root / "docs" / "readiness.json").write_text(json.dumps(readiness), encoding="utf-8")
    (root / "pyproject.toml").write_text(
        "[project]\nversion = \"3.1.0\"\nclassifiers = "
        f"[\"Development Status :: {classifier}\"]\n",
        encoding="utf-8",
    )
    (root / "STATUS.md").write_text(render_status(readiness), encoding="utf-8")


def _patch_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate_status, "ROOT", tmp_path)
    monkeypatch.setattr(validate_status, "STATUS_PATH", tmp_path / "STATUS.md")
    monkeypatch.setattr(validate_status, "READINESS_PATH", tmp_path / "docs" / "readiness.json")
    monkeypatch.setattr(validate_status, "PYPROJECT_PATH", tmp_path / "pyproject.toml")


def test_accepts_generated_conditional_release_state(tmp_path: Path, monkeypatch) -> None:
    _write_repo(tmp_path, _readiness())
    _patch_paths(tmp_path, monkeypatch)
    assert validate_status.validate_status(now="2026-08-01T00:01:00+00:00") == []


def test_rejects_version_drift(tmp_path: Path, monkeypatch) -> None:
    _write_repo(tmp_path, _readiness(project_version="3.2.0"))
    _patch_paths(tmp_path, monkeypatch)
    assert any("project_version" in e for e in validate_status.validate_status())


def test_rejects_hand_edited_status(tmp_path: Path, monkeypatch) -> None:
    _write_repo(tmp_path, _readiness())
    (tmp_path / "STATUS.md").write_text("hand edited\n", encoding="utf-8")
    _patch_paths(tmp_path, monkeypatch)
    assert any("regenerate" in e for e in validate_status.validate_status())


def test_pass_requires_every_gate_to_pass(tmp_path: Path, monkeypatch) -> None:
    state = _readiness(verdict="PASS", release_gate="ready", production_ready=True)
    _write_repo(tmp_path, state, classifier="5 - Production/Stable")
    _patch_paths(tmp_path, monkeypatch)
    assert any("all required gates" in e for e in validate_status.validate_status())


def test_conditional_state_rejects_production_stable_classifier(
    tmp_path: Path, monkeypatch
) -> None:
    _write_repo(tmp_path, _readiness(), classifier="5 - Production/Stable")
    _patch_paths(tmp_path, monkeypatch)
    assert any("Production/Stable" in e for e in validate_status.validate_status())


def test_pass_accepts_production_stable_when_all_gates_pass(
    tmp_path: Path, monkeypatch
) -> None:
    state = _readiness(
        verdict="PASS",
        release_gate="ready",
        production_ready=True,
        required_gates={
            "local_release_contract": {"status": "passing", "evidence": ["local.json"]},
            "blocking_ci_green": {"status": "passing", "evidence": ["ci.json"]},
            "live_pages_digest_and_smoke_verified": {
                "status": "passing",
                "evidence": ["deploy.json"],
            },
        },
    )
    _write_repo(tmp_path, state, classifier="5 - Production/Stable")
    _patch_paths(tmp_path, monkeypatch)
    assert validate_status.validate_status(now="2026-08-01T00:01:00+00:00") == []
