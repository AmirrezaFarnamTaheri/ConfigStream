# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from scripts import validate_workflows


def _load_local_workflow(name: str) -> dict:
    """Load one repository workflow as a mutable mapping for contract tests."""

    path = Path(__file__).resolve().parents[2] / ".github" / "workflows" / name
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _step_by_name(job: dict, name: str) -> dict:
    """Return a workflow step identified by its display name."""

    return next(
        step
        for step in job.get("steps", [])
        if isinstance(step, dict) and step.get("name") == name
    )


def test_resilient_main_contract_accepts_hardened_workflow() -> None:
    """Accept the checked-in main workflow under resilience validation."""

    assert validate_workflows._main_safe(_load_local_workflow("main.yml")) == []


def test_resilient_main_contract_requires_stage_orchestration() -> None:
    """Require main stages to run through the resilient stage orchestrator."""

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
    """Handle a valid pipeline job condition without coercion failures."""

    data = _load_local_workflow("main.yml")
    pipeline = data["jobs"]["pipeline"]
    assert isinstance(pipeline, dict)
    pipeline["if"] = "needs.setup_matrix.outputs.status == 'ready'"

    errors = validate_workflows._main_safe(data)

    assert "pipeline job-level if must not reference matrix context" not in errors


def test_pipeline_job_if_rejects_matrix_context() -> None:
    """Reject matrix references from the pipeline job-level condition."""

    data = _load_local_workflow("main.yml")
    pipeline = data["jobs"]["pipeline"]
    assert isinstance(pipeline, dict)
    pipeline["if"] = "matrix.enabled == true"

    assert (
        "pipeline job-level if must not reference matrix context"
        in validate_workflows._main_safe(data)
    )


def test_resilient_main_contract_rejects_masked_quality_failure() -> None:
    """Prevent the quality job from masking its own failure result."""

    data = deepcopy(_load_local_workflow("main.yml"))
    data["jobs"]["quality"]["continue-on-error"] = True

    assert (
        "quality job must expose its real failure result"
        in validate_workflows._main_safe(data)
    )


def test_resilient_main_contract_requires_matrix_status_evidence() -> None:
    """Require matrix-status evidence in release-readiness evaluation."""

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
    """Validate release prerequisites before expensive fan-out jobs begin."""

    data = _load_local_workflow("main.yml")
    quality = data["jobs"]["quality"]
    step = _step_by_name(quality, "Validate main release prerequisites")
    assert "scripts/preflight_release_inputs.py" in step["run"]
    assert "CS_PUBLIC_KEY" in step["env"]
    assert "CS_SIGNING_PRIVATE_KEY_HEX" in step["env"]
    assert data["jobs"]["build_container"]["needs"] == ["quality"]
    assert data["jobs"]["setup_matrix"]["needs"] == ["quality"]


def test_main_preserves_authoritative_native_report() -> None:
    """Keep one authoritative native-client report through release gating."""

    data = _load_local_workflow("main.yml")
    merge = data["jobs"]["merge_validate_publish"]
    step = _step_by_name(merge, "Run every mandatory release gate")
    command = step["run"]
    assert (
        "native_client_checks.py output --report pipeline-evidence/native_client_check_report.json"
        in command
    )
    assert (
        "--native-report pipeline-evidence/native_client_check_report.json" in command
    )
    assert "--native-report-file" not in command
    assert "CS_SIGNING_PRIVATE_KEY_HEX" not in step.get("env", {})
    release_line = next(
        line for line in command.splitlines() if "release_gate.py" in line
    )
    assert "CS_SIGNING_PRIVATE_KEY_HEX=" in release_line
    for marker in (
        "native_client_checks.py",
        "validate_pages_artifact.py",
        "generate_evidence_bundle.py",
    ):
        marker_line = next(line for line in command.splitlines() if marker in line)
        assert "CS_SIGNING_PRIVATE_KEY_HEX" not in marker_line
    assert validate_workflows._main_native_output_contract(data) is True


def test_main_contract_rejects_authoritative_native_report_overwrite() -> None:
    """Reject workflow mutations that overwrite the authoritative native report."""

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
    """Require timing evidence and reconciled metadata before release readiness."""

    data = _load_local_workflow("main.yml")
    assert str(data["env"]["SOURCE_SHARD_PARTS"]) == "6"
    merge = data["jobs"]["merge_validate_publish"]
    timing_step = _step_by_name(
        merge, "Merge and reconcile all available shard evidence"
    )
    assert "normalize_source_timing_logs.py" in timing_step["run"]
    readiness = _step_by_name(merge, "Evaluate release readiness")["run"]
    assert "--required-stage normalize-source-timings" in readiness
    assert "--required-stage reconcile-release-metadata" in readiness
    assert "--required-file pipeline-evidence/source_timing.jsonl" in readiness


def test_main_artifacts_are_stable_across_run_attempts() -> None:
    """Keep reusable artifact identities stable across rerun attempts."""

    data = _load_local_workflow("main.yml")

    wasm_upload = next(
        step
        for step in data["jobs"]["build_wasm"]["steps"]
        if isinstance(step, dict)
        and str(step.get("uses", "")).startswith("actions/upload-artifact@")
    )
    assert wasm_upload["with"]["name"] == "frontend-wasm-${{ github.run_id }}"
    assert wasm_upload["with"]["overwrite"] is True

    matrix_upload = next(
        step
        for step in data["jobs"]["setup_matrix"]["steps"]
        if isinstance(step, dict)
        and str(step.get("uses", "")).startswith("actions/upload-artifact@")
    )
    assert matrix_upload["with"]["name"] == "source-matrix-${{ github.run_id }}"
    assert matrix_upload["with"]["overwrite"] is True

    pipeline = data["jobs"]["pipeline"]
    matrix_download = next(
        step
        for step in pipeline["steps"]
        if isinstance(step, dict)
        and str(step.get("uses", "")).startswith("actions/download-artifact@")
    )
    shard_upload = next(
        step
        for step in pipeline["steps"]
        if isinstance(step, dict)
        and str(step.get("uses", "")).startswith("actions/upload-artifact@")
    )
    assert matrix_download["with"]["name"] == "source-matrix-${{ github.run_id }}"
    assert shard_upload["with"]["name"] == (
        "shard-${{ github.run_id }}-${{ matrix.batch }}-${{ matrix.part }}"
    )
    assert shard_upload["with"]["overwrite"] is True

    merge = data["jobs"]["merge_validate_publish"]
    shard_download = _step_by_name(merge, "Download shard artifacts")
    wasm_download = _step_by_name(merge, "Download WASM artifact")
    assert shard_download["with"]["pattern"] == "shard-${{ github.run_id }}-*"
    assert shard_download["with"]["merge-multiple"] is True
    assert wasm_download["with"]["name"] == "frontend-wasm-${{ github.run_id }}"

    reusable_names = [
        wasm_upload["with"]["name"],
        matrix_upload["with"]["name"],
        shard_upload["with"]["name"],
        shard_download["with"]["pattern"],
        wasm_download["with"]["name"],
    ]
    assert all("github.run_attempt" not in value for value in reusable_names)


def test_pages_contract_accepts_hardened_workflow() -> None:
    """Accept the checked-in Pages workflow under resilience validation."""

    assert (
        validate_workflows._deploy_pages_safe(_load_local_workflow("deploy-pages.yml"))
        == []
    )


def test_pages_smoke_verification_propagates_failed_stage() -> None:
    """Require deployed Pages smoke failures to propagate into stage evidence."""

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


def test_main_has_no_noncanonical_side_product_publishers() -> None:
    """Keep optional mirrors from turning a valid canonical run red."""

    data = _load_local_workflow("main.yml")
    merge = data["jobs"]["merge_validate_publish"]
    step_names = {step.get("name") for step in merge["steps"] if isinstance(step, dict)}
    assert step_names.isdisjoint(
        {
            "Publish to IPFS independently",
            "Upload to Telegram independently",
            "Upload to Hugging Face independently",
            "Upload to Google Drive independently",
            "Publish GitHub Release independently",
        }
    )

    workflow_dir = Path(__file__).resolve().parents[2] / ".github" / "workflows"
    assert not (workflow_dir / "deploy_mirror.yml").exists()
    assert "requirements-publish.txt" not in (workflow_dir / "main.yml").read_text(
        encoding="utf-8"
    )

    summary = _step_by_name(merge, "Final self-describing summary")["run"]
    assert 'stage.get("criticality", "required") == "required"' in summary
