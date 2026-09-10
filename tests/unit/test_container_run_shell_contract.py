# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from scripts.validate_workflows import _container_run_shell_errors

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"


def test_container_run_steps_resolve_to_bash() -> None:
    """All current containerized run steps must satisfy the shared validator."""

    failures: list[str] = []
    for workflow_path in sorted(WORKFLOW_DIR.glob("*.y*ml")):
        payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            continue
        failures.extend(
            f"{workflow_path.name}: {error}"
            for error in _container_run_shell_errors(payload)
        )

    assert not failures, "\n".join(failures)


def test_container_run_shell_validator_rejects_default_sh() -> None:
    workflow: dict[str, Any] = {
        "jobs": {
            "container_job": {
                "container": {"image": "example.invalid/image@sha256:deadbeef"},
                "steps": [
                    {
                        "name": "Bash-dependent step",
                        "run": "set -euo pipefail\necho ok",
                    }
                ],
            }
        }
    }

    assert _container_run_shell_errors(workflow) == [
        "container job 'container_job' run step 'Bash-dependent step' must resolve to bash"
    ]


def test_container_run_shell_validator_accepts_explicit_and_default_bash() -> None:
    explicit: dict[str, Any] = {
        "jobs": {
            "container_job": {
                "container": {"image": "example.invalid/image@sha256:deadbeef"},
                "steps": [{"run": "echo ok", "shell": "bash"}],
            }
        }
    }
    inherited: dict[str, Any] = {
        "defaults": {"run": {"shell": "bash"}},
        "jobs": {
            "container_job": {
                "container": {"image": "example.invalid/image@sha256:deadbeef"},
                "steps": [{"run": "echo ok"}],
            }
        },
    }

    assert _container_run_shell_errors(explicit) == []
    assert _container_run_shell_errors(inherited) == []
