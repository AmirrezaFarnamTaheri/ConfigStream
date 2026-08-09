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


def _step_by_name(job: dict, name: str) -> dict:
    return next(
        step
        for step in job.get("steps", [])
        if isinstance(step, dict) and step.get("name") == name
    )


def test_resilient_main_contract_accepts_hardened_workflow() -> None:
    assert validate_workflows._main_safe(_load_local_workflow("main.yml")) == []


def test_resilient_main_contract_requires_stage_orchestration() -> None:
    data = deepcopy(_load_local_workflow("main.yml"))
    for job in data["jobs"].values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []):
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                step["run"] = step["run"].replace(
                    "scripts/resilient_stage.py", "scripts/legacy_stage.py"
                )

    assert (
        "main workflow must orchestrate stages through scripts/resilient_stage.py"
        in validate_workflows._main_safe(data)
    )


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
            step["run"] = step["run"].replace("--required-stage matrix-status \\\n", "")

    assert (
        "release readiness must require matrix-status"
        in validate_workflows._main_safe(data)
    )


def test_main_release_prerequisites_are_checked_before_fanout() -> None:
    data = _load_local_workflow("main.yml")
    quality = data["jobs"]["quality"]
    step = _step_by_name(quality, "Validate main release prerequisites")
    assert "scripts/preflight_release_inputs.py" in step["run"]
    assert "CS_PUBLIC_KEY" in step["env"]
    assert "CS_SIGNING_PRIVATE_KEY_HEX" in step["env"]
    assert data["jobs"]["build_container"]["needs"] == ["quality"]
    assert data["jobs"]["setup_matrix"]["needs"] == ["quality"]


def test_main_preserves_authoritative_native_report() -> None:
    data = _load_local_workflow("main.yml")
    merge = data["jobs"]["merge_validate_publish"]
    step = _step_by_name(merge, "Run every mandatory release gate")
    command = step["run"]
    assert "native_client_checks.py output --report pipeline-evidence/native_client_check_report.json" in command
    assert "--native-report pipeline-evidence/native_client_check_report.json" in command
    assert "--native-report-file" not in command
    assert "CS_SIGNING_PRIVATE_KEY_HEX" in step["env"]
    assert validate_workflows._main_native_output_contract(data) is True


def test_main_contract_rejects_authoritative_native_report_overwrite() -> None:
    data = deepcopy(_load_local_workflow("main.yml"))
    merge = data["jobs"]["merge_validate_publish"]
    step = _step_by_name(merge, "Run every mandatory release gate")
    step["run"] = step["run"].replace(
        "validate_pages_artifact.py --native-client-check output",
        "validate_pages_artifact.py --native-client-check "
        "--native-report-file pipeline-evidence/native_client_check_report.json output",
    )

    assert validate_workflows._main_native_output_contract(data) is False
    assert (
        "data release assets must use the shared native output contract"
        in validate_workflows._main_safe(data)
    )


def test_main_requires_real_timing_and_reconciled_public_metadata() -> None:
    data = _load_local_workflow("main.yml")
    assert str(data["env"]["SOURCE_SHARD_PARTS"]) == "6"
    merge = data["jobs"]["merge_validate_publish"]
    timing_step = _step_by_name(merge, "Merge and reconcile all available shard evidence")
    assert "normalize_source_timing_logs.py" in timing_step["run"]
    readiness = _step_by_name(merge, "Evaluate release readiness")["run"]
    assert "--required-stage normalize-source-timings" in readiness
    assert "--required-stage reconcile-release-metadata" in readiness
    assert "--required-file pipeline-evidence/source_timing.jsonl" in readiness


def test_pages_contract_accepts_hardened_workflow() -> None:
    assert (
        validate_workflows._deploy_pages_safe(_load_local_workflow("deploy-pages.yml"))
        == []
    )


def test_pages_smoke_verification_propagates_failed_stage() -> None:
    data = _load_local_workflow("deploy-pages.yml")
    deploy = data["jobs"]["deploy"]
    smoke_step = next(
        step
        for step in deploy["steps"]
        if isinstance(step, dict) and step.get("name") == "Smoke deployed Pages URL"
    )
    command = smoke_step.get("run", "")

    assert "deploy-evidence/stages/smoke-pages.json" in command
    assert 'test "$smoke_status" = success' in command
