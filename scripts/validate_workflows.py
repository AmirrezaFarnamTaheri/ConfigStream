# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate GitHub Actions syntax and fail-closed publication contracts."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
CONCURRENCY_REQUIRED = {
    "main.yml",
    "retest.yml",
    "deploy-pages.yml",
    "deploy_mirror.yml",
}
UNRESOLVABLE_ACTION_REFS = {
    "actions/cache@0c907a75c2df011682e883a1779590213020689b",
    "actions/deploy-pages@d6db90164db5ed868d4d441e8835172955749614",
    "actions/setup-go@f111f3307d8850f5010000d3170f7d54b8f037b5",
    "actions/setup-python@f67e24a430187b32086e1643ad3e03d6861f5b15",
    "actions/upload-pages-artifact@56afc609e74202658d3ffba0e8f6dda9c69ecc6b",
    "docker/build-push-action@471d19853a5250da73d4d382db29e5b02da898a3",
    "docker/setup-buildx-action@b167a82b8f5039d57a2e041d08e59653a1a9e710",
    "gitleaks/gitleaks-action@f0ab97193b0400b14c330f2fb1640520608fa20e",
}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _jobs(data: dict[Any, Any]) -> dict[Any, Any]:
    jobs = data.get("jobs", {})
    return jobs if isinstance(jobs, dict) else {}


def _iter_steps(data: dict[Any, Any]) -> list[dict[Any, Any]]:
    steps: list[dict[Any, Any]] = []
    for job in _jobs(data).values():
        if not isinstance(job, dict):
            continue
        job_steps = job.get("steps", [])
        if isinstance(job_steps, list):
            steps.extend(step for step in job_steps if isinstance(step, dict))
    return steps


def _step_uses(step: dict[Any, Any], prefix: str) -> bool:
    value = step.get("uses")
    return isinstance(value, str) and value.startswith(prefix)


def _step_with(step: dict[Any, Any]) -> dict[Any, Any]:
    value = step.get("with", {})
    return value if isinstance(value, dict) else {}


def _run(step: dict[Any, Any]) -> str:
    value = step.get("run")
    return value if isinstance(value, str) else ""


def _run_steps(data: dict[Any, Any]) -> Iterable[str]:
    for step in _iter_steps(data):
        command = _run(step)
        if command:
            yield command


def _has_command(data: dict[Any, Any], text: str) -> bool:
    return any(text in command for command in _run_steps(data))


def _has_action(data: dict[Any, Any], prefix: str) -> bool:
    return any(_step_uses(step, prefix) for step in _iter_steps(data))


def _retention_days(step: dict[Any, Any]) -> Optional[int]:
    try:
        return int(str(_step_with(step).get("retention-days")))
    except (TypeError, ValueError):
        return None


def _has_durable_named_artifact(
    data: dict[Any, Any], *, action: str, artifact_name: str
) -> bool:
    for step in _iter_steps(data):
        if not _step_uses(step, action):
            continue
        if _step_with(step).get("name") != artifact_name:
            continue
        retention = _retention_days(step)
        return retention is not None and retention >= 30
    return False


def _has_named_artifact(
    data: dict[Any, Any], *, action: str, artifact_name: str
) -> bool:
    return any(
        _step_uses(step, action) and _step_with(step).get("name") == artifact_name
        for step in _iter_steps(data)
    )


def _has_durable_pages_artifact(data: dict[Any, Any]) -> bool:
    return any(
        _step_uses(step, "actions/upload-pages-artifact@")
        and (_retention_days(step) or 0) >= 30
        for step in _iter_steps(data)
    )


def _job_needs(job: dict[Any, Any], required: str) -> bool:
    needs = job.get("needs")
    if isinstance(needs, str):
        return needs == required
    if isinstance(needs, list):
        return required in {str(item) for item in needs}
    return False


def _find_job(data: dict[Any, Any], name: str) -> Optional[dict[Any, Any]]:
    job = _jobs(data).get(name)
    return job if isinstance(job, dict) else None


def _find_step(data: dict[Any, Any], name: str) -> Optional[dict[Any, Any]]:
    for step in _iter_steps(data):
        if step.get("name") == name:
            return step
    return None


def _contains_secret_context_in_if(data: object) -> bool:
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "if" and isinstance(value, str) and "secrets." in value:
                return True
            if _contains_secret_context_in_if(value):
                return True
    elif isinstance(data, list):
        return any(_contains_secret_context_in_if(item) for item in data)
    return False


def _find_unresolvable_action_refs(data: dict[Any, Any]) -> list[str]:
    refs = {
        str(step.get("uses"))
        for step in _iter_steps(data)
        if isinstance(step.get("uses"), str)
    }
    return sorted(ref for ref in UNRESOLVABLE_ACTION_REFS if ref in refs)


def _has_contract_validators(data: dict[Any, Any]) -> bool:
    return all(
        _has_command(data, command)
        for command in (
            "python scripts/validate_capability_registry.py",
            "python scripts/validate_core_compatibility.py",
            "python scripts/validate_module_ownership.py",
        )
    )


def _ci_safe(data: dict[Any, Any]) -> list[str]:
    errors: list[str] = []
    frontend = _find_job(data, "frontend")
    browser = _find_job(data, "frontend-browser")
    browser_commands = (
        "\n".join(
            _run(step) for step in browser.get("steps", []) if isinstance(step, dict)
        )
        if browser
        else ""
    )
    if not all(
        text in browser_commands
        for text in (
            "python -m playwright install --with-deps chromium",
            "npx playwright install chromium",
            "npm run test:frontend:browser",
        )
    ):
        errors.append("missing required frontend-browser Playwright profile")
    frontend_commands = (
        "\n".join(
            _run(step) for step in frontend.get("steps", []) if isinstance(step, dict)
        )
        if frontend
        else ""
    )
    if not all(
        text in frontend_commands
        for text in (
            "npx playwright install chromium",
            "npm run test:frontend:no-network",
        )
    ):
        errors.append("frontend smoke job must install Node Playwright Chromium")
    if not _has_command(
        data, "bandit -r src/configstream scripts tools"
    ) or not _has_command(
        data, "python scripts/validate_bandit_suppressions.py --require-active"
    ):
        errors.append("missing Bandit suppression hygiene guard")
    if not _has_command(data, "python scripts/validate_test_skips.py"):
        errors.append("missing pytest skip governance guard")
    if not _has_contract_validators(data):
        errors.append("missing capability/core/module ownership contract validators")
    return errors


def _main_public_preparation(data: dict[Any, Any]) -> bool:
    transactional = (
        _has_command(data, "scripts/prepare_public_candidate.py output output")
        and _has_command(
            data,
            "validate_frontend_placeholders.py --inject-env --strict output",
        )
        and _has_command(data, "validate_pages_artifact.py --refresh-contract output")
    )
    legacy = all(
        _has_command(data, command)
        for command in (
            "cp -R frontend/. output/",
            "mkdir -p output/tools output/api",
            "validate_frontend_placeholders.py --inject-env output",
            "cp output/proxies.json output/api/proxies",
            "cp output/metadata.json output/api/stats",
            "output/pipeline_events.jsonl",
            "validate_pages_artifact.py --refresh-contract output",
        )
    )
    return transactional or legacy


def _main_wasm_download_has_dependency(data: dict[Any, Any]) -> bool:
    for job in _jobs(data).values():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps", [])
        if not isinstance(steps, list):
            continue
        downloads_wasm = any(
            isinstance(step, dict)
            and _step_uses(step, "actions/download-artifact@")
            and str(_step_with(step).get("name", "")).startswith("frontend-wasm")
            for step in steps
        )
        if downloads_wasm and not _job_needs(job, "build_wasm"):
            return False
    return True


def _main_resilient_contract(data: dict[Any, Any]) -> list[str]:
    if not _has_command(data, "scripts/resilient_stage.py"):
        return []
    errors: list[str] = []
    quality = _find_job(data, "quality")
    matrix = _find_job(data, "setup_matrix")
    pipeline = _find_job(data, "pipeline")
    merge = _find_job(data, "merge_validate_publish")
    if quality is None or quality.get("continue-on-error") is True:
        errors.append("quality job must expose its real failure result")
    if matrix is None or matrix.get("continue-on-error") is True:
        errors.append("setup_matrix job must expose its real failure result")
    if pipeline is None or pipeline.get("continue-on-error") is True:
        errors.append("pipeline job must expose its real failure result")
    pipeline_if = str(pipeline.get("if", "")) if pipeline else ""
    if re.search(r"(?<![A-Za-z0-9_])matrix\.", pipeline_if):
        errors.append("pipeline job-level if must not reference matrix context")
    if (
        matrix is None
        or not isinstance(matrix.get("outputs"), dict)
        or "status" not in matrix["outputs"]
    ):
        errors.append("setup_matrix must expose a status output")
    if merge is None:
        errors.append("missing merge_validate_publish diagnostic gate")
        return errors
    merge_commands = "\n".join(
        _run(step) for step in merge.get("steps", []) if isinstance(step, dict)
    )
    for stage in ("quality-job", "matrix-status", "shard-jobs", "restore-wasm"):
        if f"--required-stage {stage}" not in merge_commands:
            errors.append(f"release readiness must require {stage}")
    if "record --name matrix-status" not in merge_commands:
        errors.append("matrix status must be recorded as release evidence")
    if "scripts/prepare_public_candidate.py output output" not in merge_commands:
        errors.append("public candidate replacement must be transactional")
    if "bash scripts/install_native_validators.sh" not in merge_commands:
        errors.append(
            "native validator installation must use the shared verified installer"
        )
    prepare_step = _find_step(data, "Prepare public output artifact transactionally")
    if prepare_step and "rm -rf output" in _run(prepare_step):
        errors.append("public candidate preparation must preserve output on failure")
    return errors


def _main_safe(data: dict[Any, Any]) -> list[str]:
    errors: list[str] = []
    if _has_command(data, "git push"):
        errors.append("main workflow must not push commits")
    if not (
        _has_command(data, "python scripts/dynamic_reshard.py")
        and _has_named_artifact(
            data,
            action="actions/upload-artifact@",
            artifact_name="source-reshard-recommendation",
        )
    ):
        errors.append("dynamic resharding must publish an artifact recommendation")
    if not _has_durable_named_artifact(
        data,
        action="actions/upload-artifact@",
        artifact_name="pipeline-output",
    ):
        errors.append("pipeline-output artifact must retain for >=30 days")
    if not (
        _has_command(data, "python scripts/validate_pages_artifact.py")
        and _has_command(data, "--native-client-check")
        and _has_command(
            data,
            "--native-report-file pipeline-evidence/native_client_check_report.json",
        )
    ):
        errors.append("data release assets must use the shared native output contract")
    if not _main_public_preparation(data):
        errors.append("data release validation must prepare the public output artifact")
    if not _main_wasm_download_has_dependency(data):
        errors.append("WASM artifact consumers must depend on build_wasm")
    errors.extend(_main_resilient_contract(data))
    return errors


def _deploy_pages_safe(data: dict[Any, Any]) -> list[str]:
    errors: list[str] = []
    if not _has_durable_pages_artifact(data):
        errors.append("Pages artifact upload must retain for >=30 days")
    if not _has_action(data, "actions/deploy-pages@"):
        errors.append("missing Pages deployment action")
    if not (
        _has_command(data, "validate_frontend_placeholders.py --strict output")
        and _has_command(data, "validate_pages_artifact.py output")
    ):
        errors.append("missing immutable sealed artifact validation")
    if not (
        _has_command(data, "scripts/verify_pages_deployment.py")
        and _has_command(data, "steps.deployment.outputs.page_url")
    ):
        errors.append("missing deployed Pages URL smoke validation")
    commands = "\n".join(_run_steps(data))
    if (
        "npm run build" in commands
        or "vite build" in commands
        or "frontend-dist" in commands
    ):
        errors.append("Pages must not rebuild frontend assets")
    serialized = yaml.safe_dump(data, sort_keys=False)
    if "STEGO_KEY" in serialized:
        errors.append("Pages must not receive symmetric secrets")
    concurrency = data.get("concurrency")
    if (
        not isinstance(concurrency, dict)
        or concurrency.get("cancel-in-progress") is not False
    ):
        errors.append(
            "Pages deployments must queue instead of cancelling in-progress releases"
        )
    locate = _find_step(data, "Locate and download exact canonical artifact")
    if (
        locate is None
        or "set -euo pipefail" not in _run(locate)
        or "set +e" in _run(locate)
    ):
        errors.append(
            "Pages artifact lookup must use strict, narrowly scoped error handling"
        )
    if not (
        _has_command(data, "--required-stage deployment-evidence-bundle")
        and _has_command(data, "deployment_readiness.json")
        and _has_command(data, "stage_summary.json")
    ):
        errors.append("Pages deployment must produce final fail-closed evidence")
    return errors


def main() -> int:
    if not WORKFLOW_DIR.exists():
        print(f"ERROR: workflow directory not found: {WORKFLOW_DIR}")
        return 1
    workflow_files = sorted(
        path for pattern in ("*.yml", "*.yaml") for path in WORKFLOW_DIR.glob(pattern)
    )
    if not workflow_files:
        print(f"ERROR: no workflow files found in {WORKFLOW_DIR}")
        return 1

    errors: list[str] = []
    for path in workflow_files:
        try:
            data = yaml.safe_load(_text(path))
        except yaml.YAMLError as exc:
            errors.append(f"{path}: YAML parse failed: {exc}")
            continue
        except OSError as exc:
            errors.append(f"{path}: could not read file: {exc}")
            continue
        if not isinstance(data, dict) or ("on" not in data and True not in data):
            errors.append(f"{path}: invalid workflow root")
            continue
        if not _jobs(data):
            errors.append(f"{path}: missing jobs")
            continue
        if path.name in CONCURRENCY_REQUIRED and "concurrency" not in data:
            errors.append(f"{path}: missing concurrency")
        if _contains_secret_context_in_if(data):
            errors.append(
                f"{path}: secrets context must not be used directly in if expressions"
            )
        for ref in _find_unresolvable_action_refs(data):
            errors.append(f"{path}: stale action ref {ref}")
        if path.name == "ci.yml":
            errors.extend(f"{path}: {error}" for error in _ci_safe(data))
        if path.name == "release.yml" and not _has_contract_validators(data):
            errors.append(
                f"{path}: missing capability/core/module ownership contract validators"
            )
        if path.name == "main.yml":
            errors.extend(f"{path}: {error}" for error in _main_safe(data))
        if path.name == "retest.yml" and not _has_durable_named_artifact(
            data,
            action="actions/upload-artifact@",
            artifact_name="pipeline-output",
        ):
            errors.append(f"{path}: pipeline-output artifact retention must be durable")
        if path.name == "deploy-pages.yml":
            errors.extend(f"{path}: {error}" for error in _deploy_pages_safe(data))
        if _has_command(data, "git push"):
            errors.append(f"{path}: workflows must not push directly to the repository")

    if errors:
        print("ERROR: workflow validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"OK: validated {len(workflow_files)} workflow files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
