# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for workflow YAML validation."""

from __future__ import annotations

from pathlib import Path

from scripts import validate_workflows


def test_validate_workflows_accepts_current_repo_workflows() -> None:
    assert validate_workflows.main() == 0


def test_validate_workflows_reports_yaml_errors(tmp_path: Path, monkeypatch) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "broken.yml").write_text(
        "name: Broken\non: [push\njobs: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1
