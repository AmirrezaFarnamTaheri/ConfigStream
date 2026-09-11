# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from scripts.validate_workflows import _container_bash_shell_errors

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"


def test_container_bash_only_steps_resolve_to_bash() -> None:
    failures: list[str] = []
    for workflow_path in sorted(WORKFLOW_DIR.glob("*.y*ml")):
        if workflow_path.name.startswith("temporary-"):
            continue
        payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
        if isinstance(payload, dict):
            failures.extend(
                f"{workflow_path.name}: {error}"
                for error in _container_bash_shell_errors(payload)
            )
    assert not failures, "\n".join(failures)


def _container(run: str, **job_fields: Any) -> dict[str, Any]:
    job = {
        "container": {"image": "example.invalid/image@sha256:deadbeef"},
        "steps": [{"name": "strict", "run": run}],
    }
    job.update(job_fields)
    return {"jobs": {"container_job": job}}


def test_container_shell_validator_rejects_default_sh_for_bash_syntax() -> None:
    assert (
        len(_container_bash_shell_errors(_container("set -euo pipefail\necho ok"))) == 1
    )


def test_container_shell_validator_accepts_step_job_and_workflow_bash() -> None:
    explicit = _container("set -euo pipefail\necho ok")
    explicit["jobs"]["container_job"]["steps"][0]["shell"] = "bash"
    inherited_job = _container(
        "set -euo pipefail\necho ok",
        defaults={"run": {"shell": "bash"}},
    )
    inherited_workflow = _container("set -euo pipefail\necho ok")
    inherited_workflow["defaults"] = {"run": {"shell": "bash"}}
    assert _container_bash_shell_errors(explicit) == []
    assert _container_bash_shell_errors(inherited_job) == []
    assert _container_bash_shell_errors(inherited_workflow) == []


def test_posix_only_container_command_does_not_require_bash() -> None:
    assert _container_bash_shell_errors(_container("echo ok")) == []


def test_extended_bash_only_markers_are_guarded() -> None:
    for command in (
        "declare -a values=()",
        "declare -A values=()",
        "readarray values < input.txt",
        "source ./env.sh",
        "cat <(printf ok)",
        "cat <<< value",
    ):
        assert _container_bash_shell_errors(_container(command)), command
