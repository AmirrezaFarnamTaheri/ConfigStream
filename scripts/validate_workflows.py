# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate GitHub Actions workflow YAML files and release safety contracts."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

WORKFLOW_DIR = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def _steps(data: Dict[Any, Any]) -> List[Dict[Any, Any]]:
    result: List[Dict[Any, Any]] = []
    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict):
        return result
    for job in jobs.values():
        if isinstance(job, dict):
            for step in job.get("steps", []):
                if isinstance(step, dict):
                    result.append(step)
    return result


def _run(step: Dict[Any, Any]) -> str:
    value = step.get("run", "")
    return value if isinstance(value, str) else ""


def _uses(step: Dict[Any, Any], prefix: str) -> bool:
    value = step.get("uses", "")
    return isinstance(value, str) and value.startswith(prefix)


def _with(step: Dict[Any, Any]) -> Dict[Any, Any]:
    value = step.get("with", {})
    return value if isinstance(value, dict) else {}


def _jobs(data: Dict[Any, Any]) -> Dict[Any, Any]:
    value = data.get("jobs", {})
    return value if isinstance(value, dict) else {}


def _job(data: Dict[Any, Any], name: str) -> Optional[Dict[Any, Any]]:
    value = _jobs(data).get(name)
    return value if isinstance(value, dict) else None


def _job_text(job: Optional[Dict[Any, Any]]) -> str:
    if not job:
        return ""
    return "\n".join(_run(step) for step in job.get("steps", []) if isinstance(step, dict))


def _retention(step: Dict[Any, Any]) -> Optional[int]:
    value = _with(step).get("retention-days")
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _artifact_ok(data: Dict[Any, Any], name: str, action: str) -> bool:
    for step in _steps(data):
        if _uses(step, action) and _with(step).get("name") == name:
            days = _retention(step)
            return days is not None and days >= 30
    return False


def _main_safe(data: Dict[Any, Any]) -> List[str]:
    errors: List[str] = []
    text = _job_text(_job(data, "merge_validate_publish"))
    if "rm -rf output" in text:
        errors.append("release preparation must not delete output unconditionally")
    for required in ("quality-job", "matrix-status", "shard-jobs", "restore-wasm"):
        if f"--required-stage {required}" not in text:
            errors.append(f"missing readiness stage {required}")
    if "matrix.enabled" in str(_job(data, "pipeline") or {}).get("if", ""):
        errors.append("pipeline job if cannot reference matrix")
    if "needs.setup_matrix.outputs.status == 'ready'" not in str((_job(data, "pipeline") or {}).get("if", "")):
        errors.append("pipeline must require ready matrix status")
    if not _artifact_ok(data, "pipeline-output", "actions/upload-artifact@"):
        errors.append("pipeline-output artifact retention must be >=30 days")
    return errors


def _pages_safe(data: Dict[Any, Any]) -> List[str]:
    errors: List[str] = []
    concurrency = data.get("concurrency", {})
    if not isinstance(concurrency, dict) or concurrency.get("cancel-in-progress") is not False:
        errors.append("Pages deployment must not cancel in-flight deploys")
    text = _job_text(_job(data, "deploy"))
    if "set +e" in text:
        errors.append("Pages workflow must not disable shell errors globally")
    if "verify_pages_deployment.py" not in text:
        errors.append("missing Pages smoke validation")
    if "deployment-evidence-bundle" not in text:
        errors.append("missing deployment evidence bundle")
    return errors


def main() -> int:
    errors: List[str] = []
    for path in sorted([*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")]):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{path}: YAML parse failed: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path}: invalid workflow")
            continue
        if path.name == "main.yml":
            errors.extend(f"{path}: {item}" for item in _main_safe(data))
        if path.name == "deploy-pages.yml":
            errors.extend(f"{path}: {item}" for item in _pages_safe(data))
    if errors:
        print("ERROR: workflow validation failed")
        for error in errors:
            print(error)
        return 1
    print("OK: workflow contracts validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
