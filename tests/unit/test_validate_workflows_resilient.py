# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from scripts import validate_workflows


def _load_local_workflow(name: str) -> dict:
    path = Path(__file__).resolve().parents[2] / ".github" / "workflows" / name
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_resilient_main_contract_accepts_hardened_workflow() -> None:
    assert validate_workflows._main_safe(_load_local_workflow("main.yml")) == []


def test_pipeline_job_if_is_read_without_string_conversion_crash() -> None:
    data = _load_local_workflow("main.yml")
    pipeline = data["jobs"]["pipeline"]
    assert isinstance(pipeline, dict)
    pipeline["if"] = "needs.setup_matrix.outputs.status == 'ready'"

    errors = validate_workflows._main_safe(data)

    assert "pipeline job-level if must not reference matrix context" not in errors


def test_pipeline_job_if_rejects_matrix_context() -> None:
    data = _load_local_workflow("main.yml")
    pipeline = data["jobs"]["pipeline"]
    assert isinstance(pipeline, dict)
    pipeline["if"] = "matrix.enabled == true"

    assert (
        "pipeline job-level if must not reference matrix context"
        in validate_workflows._main_safe(data)
    )


def test_resilient_main_contract_rejects_masked_quality_failure() -> None:
    data = deepcopy(_load_local_workflow("main.yml"))
    data["jobs"]["quality"]["continue-on-error"] = True

    assert (
        "quality job must expose its real failure result"
        in validate_workflows._main_safe(data)
    )


def test_resilient_main_contract_requires_matrix_status_evidence() -> None:
    data = deepcopy(_load_local_workflow("main.yml"))
    merge = data["jobs"]["merge_validate_publish"]
    for step in merge["steps"]:
        if isinstance(step, dict) and isinstance(step.get("run"), str):
            step["run"] = step["run"].replace(
                "--required-stage matrix-status \\\n", ""
            )

    assert (
        "release readiness must require matrix-status"
        in validate_workflows._main_safe(data)
    )


def test_pages_contract_accepts_hardened_workflow() -> None:
    assert (
        validate_workflows._deploy_pages_safe(
            _load_local_workflow("deploy-pages.yml")
        )
        == []
    )
