# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from scripts import validate_container_shells


def test_rejects_bash_only_syntax_under_container_default_sh() -> None:
    workflow = {
        "jobs": {
            "geoip": {
                "container": {"image": "example.invalid/image@sha256:deadbeef"},
                "steps": [
                    {"name": "Strict shell", "run": "set -euo pipefail\necho ok"}
                ],
            }
        }
    }
    errors = validate_container_shells.validate_workflow(workflow)
    assert len(errors) == 1
    assert "Strict shell" in errors[0]
    assert "shell: bash" in errors[0]


def test_accepts_job_and_workflow_level_bash_defaults() -> None:
    job_default = {
        "jobs": {
            "geoip": {
                "container": {"image": "example.invalid/image@sha256:deadbeef"},
                "defaults": {"run": {"shell": "bash"}},
                "steps": [{"run": "set -euo pipefail\necho ok"}],
            }
        }
    }
    workflow_default = {
        "defaults": {"run": {"shell": "bash"}},
        "jobs": {
            "geoip": {
                "container": {"image": "example.invalid/image@sha256:deadbeef"},
                "steps": [{"run": "set -euo pipefail\necho ok"}],
            }
        },
    }
    assert validate_container_shells.validate_workflow(job_default) == []
    assert validate_container_shells.validate_workflow(workflow_default) == []


def test_accepts_step_level_bash_shell() -> None:
    workflow = {
        "jobs": {
            "geoip": {
                "container": {"image": "example.invalid/image@sha256:deadbeef"},
                "steps": [{"shell": "bash", "run": "set -euo pipefail\necho ok"}],
            }
        }
    }
    assert validate_container_shells.validate_workflow(workflow) == []


def test_repository_workflows_satisfy_container_shell_contract() -> None:
    assert validate_container_shells.main() == 0
