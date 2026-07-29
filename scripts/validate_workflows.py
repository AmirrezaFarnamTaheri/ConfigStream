# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate GitHub Actions workflow YAML files and release safety contracts."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

WORKFLOW_DIR = Path(".github") / "workflows"
CONCURRENCY_REQUIRED = {"main.yml", "retest.yml", "deploy-pages.yml", "deploy_mirror.yml"}
UNRESOLVABLE_ACTION_REFS = {
    "actions/cache@0c907a75c2df011682e883a1779590213020689b",
    "actions/deploy-pages@d6db90164db5ed868d4d441e8835172955749614",
    "actions/setup-go@f111f3307d8850f5010000d3170f7d54b8f037b5",
    "actions/setup-python@f67e24a430187b32086e1643ad3e03d6861f5b15",
    "actions/upload-pages-artifact@56afc609e74202658d3ffba0e8f6dda9c69ecc6b",
}


def _iter_steps(data: dict[Any, Any]) -> list[dict[Any, Any]]:
    steps: list[dict[Any, Any]] = []
    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict):
        return steps
    for job in jobs.values():
        if isinstance(job, dict):
            steps.extend(step for step in job.get("steps", []) if isinstance(step, dict))
    return steps


def _uses(step: dict[Any, Any], prefix: str) -> bool:
    value = step.get("uses")
    return isinstance(value, str) and value.startswith(prefix)


def _with(step: dict[Any, Any]) -> dict[Any, Any]:
    return step.get("with", {}) if isinstance(step.get("with", {}), dict) else {}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _has_durable_artifact(data: dict[Any, Any], name: str, action: str) -> bool:
    for step in _iter_steps(data):
        if _uses(step, action) and _with(step).get("name") == name:
            try:
                return int(str(_with(step).get("retention-days"))) >= 30
            except (TypeError, ValueError):
                return False
    return False


def _contains_git_push(path: Path) -> bool:
    return "git push" in _text(path)


def _deploy_pages_safe(path: Path) -> list[str]:
    errors: list[str] = []
    content = _text(path)
    if "actions/upload-pages-artifact@" not in content:
        errors.append("missing Pages artifact upload")
    if "actions/deploy-pages@" not in content:
        errors.append("missing Pages deployment")
    if "npm run build" in content or "vite build" in content:
        errors.append("Pages must not rebuild frontend")
    if "STEGO_KEY" in content:
        errors.append("Pages must not receive symmetric secrets")
    if "verify_pages_deployment.py" not in content:
        errors.append("missing public smoke validation")
    return errors


def _main_safe(path: Path, data: dict[Any, Any]) -> list[str]:
    errors: list[str] = []
    content = _text(path)
    if _contains_git_push(path):
        errors.append("main workflow must not push commits")
    if "scripts/resilient_stage.py" not in content:
        errors.append("missing resilient stage evidence")
    if "release_readiness.json" not in content:
        errors.append("missing readiness report")
    if "pipeline-output" in content and not _has_durable_artifact(data, "pipeline-output", "actions/upload-artifact@"):
        errors.append("pipeline-output artifact must retain for >=30 days")
    if "scripts/prepare_public_candidate.py" not in content:
        errors.append("missing transactional candidate preparation")
    return errors


def main() -> int:
    if not WORKFLOW_DIR.exists():
        print(f"ERROR: workflow directory not found: {WORKFLOW_DIR}")
        return 1
    errors: list[str] = []
    for path in sorted([*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")]):
        try:
            data = yaml.safe_load(_text(path))
        except yaml.YAMLError as exc:
            errors.append(f"{path}: YAML parse failed: {exc}")
            continue
        if not isinstance(data, dict) or ("on" not in data and True not in data):
            errors.append(f"{path}: invalid workflow root")
            continue
        if not isinstance(data.get("jobs"), dict) or not data["jobs"]:
            errors.append(f"{path}: missing jobs")
        if path.name in CONCURRENCY_REQUIRED and "concurrency" not in data:
            errors.append(f"{path}: missing concurrency")
        for ref in UNRESOLVABLE_ACTION_REFS:
            if ref in _text(path):
                errors.append(f"{path}: stale action ref {ref}")
        if path.name == "main.yml":
            errors.extend(f"{path}: {e}" for e in _main_safe(path, data))
        if path.name == "deploy-pages.yml":
            errors.extend(f"{path}: {e}" for e in _deploy_pages_safe(path))
    if errors:
        print("ERROR: workflow validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: workflow contracts validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
