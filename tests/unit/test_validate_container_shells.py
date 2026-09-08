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

    assert validate_container_shells.validate_workflow(workflow) == [
        "container job geoip step 'Strict shell' uses Bash-only syntax without an explicit Bash shell"
    ]


def test_accepts_job_level_bash_default() -> None:
    workflow = {
        "jobs": {
            "geoip": {
                "container": {"image": "example.invalid/image@sha256:deadbeef"},
                "defaults": {"run": {"shell": "bash"}},
                "steps": [
                    {"name": "Strict shell", "run": "set -euo pipefail\necho ok"}
                ],
            }
        }
    }

    assert validate_container_shells.validate_workflow(workflow) == []


def test_accepts_step_level_bash_shell() -> None:
    workflow = {
        "jobs": {
            "geoip": {
                "container": {"image": "example.invalid/image@sha256:deadbeef"},
                "steps": [
                    {
                        "name": "Strict shell",
                        "shell": "bash",
                        "run": "set -euo pipefail\necho ok",
                    }
                ],
            }
        }
    }

    assert validate_container_shells.validate_workflow(workflow) == []
