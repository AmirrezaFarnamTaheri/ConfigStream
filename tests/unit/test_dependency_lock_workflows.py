# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

from scripts.check_dependency_drift import (
    check_publisher_pins,
    check_workflow_dependency_installs,
)


def test_publisher_entry_points_are_exactly_pinned() -> None:
    assert check_publisher_pins(Path("requirements-publish.txt")) == []


def test_workflows_install_from_reviewed_requirement_files() -> None:
    assert check_workflow_dependency_installs(Path(".github/workflows")) == []


def test_ad_hoc_workflow_install_is_rejected(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("run: pip install -e .[dev]\n", encoding="utf-8")
    errors = check_workflow_dependency_installs(workflows)
    assert any("ad hoc" in error for error in errors)
