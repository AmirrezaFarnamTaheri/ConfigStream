# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for container-job shell semantics."""

import pytest

from scripts import validate_workflows


def test_container_job_rejects_bash_only_syntax_without_bash_shell() -> None:
    workflow = {
        "jobs": {
            "geoip": {
                "container": {"image": "example.invalid/image@sha256:deadbeef"},
                "steps": [
                    {
                        "name": "Prepare GeoIP",
                        "run": "set -euo pipefail\necho ready\n",
                    }
                ],
            }
        }
    }

    errors = validate_workflows._container_bash_shell_errors(workflow)

    assert len(errors) == 1
    assert "Prepare GeoIP" in errors[0]
    assert "shell: bash" in errors[0]


@pytest.mark.parametrize(
    "command",
    [
        "values=(one two)\nprintf '%s\\n' \"${values[@]}\"\n",
        "count=0\n((count++))\n",
        "value=abc\nif [[ $value =~ ^a ]]; then echo match; fi\n",
    ],
)
def test_container_job_rejects_additional_bash_grammar_without_bash_shell(
    command: str,
) -> None:
    workflow = {
        "jobs": {
            "container-job": {
                "container": {"image": "example.invalid/image@sha256:deadbeef"},
                "steps": [{"name": "Bash grammar", "run": command}],
            }
        }
    }

    errors = validate_workflows._container_bash_shell_errors(workflow)

    assert len(errors) == 1
    assert "Bash grammar" in errors[0]


def test_container_job_accepts_job_level_bash_default() -> None:
    workflow = {
        "jobs": {
            "geoip": {
                "container": {"image": "example.invalid/image@sha256:deadbeef"},
                "defaults": {"run": {"shell": "bash"}},
                "steps": [
                    {
                        "name": "Prepare GeoIP",
                        "run": "set -euo pipefail\necho ready\n",
                    }
                ],
            }
        }
    }

    assert validate_workflows._container_bash_shell_errors(workflow) == []


def test_container_job_accepts_step_level_bash_shell() -> None:
    workflow = {
        "jobs": {
            "pipeline": {
                "container": {"image": "example.invalid/image@sha256:deadbeef"},
                "steps": [
                    {
                        "name": "Run shard",
                        "shell": "bash",
                        "run": "set -o pipefail\necho done | tee output.log\n",
                    }
                ],
            }
        }
    }

    assert validate_workflows._container_bash_shell_errors(workflow) == []
