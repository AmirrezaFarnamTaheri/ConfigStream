# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate GitHub Actions workflow YAML files and release invariants."""

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
    "docker/build-push-action@471d19853a5250da73d4d382db29e5b02da898a3",
    "docker/setup-buildx-action@b167a82b8f5039d57a2e041d08e59653a1a9e710",
    "gitleaks/gitleaks-action@f0ab97193b0400b14c330f2fb1640520608fa20e",
}


def _trigger_block(data: dict[Any, Any]) -> Any:
    return data.get("on", data.get(True))


def _iter_steps(data: dict[Any, Any]) -> list[dict[Any, Any]]:
    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict):
        return []
    result: list[dict[Any, Any]] = []
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps", [])
        if isinstance(steps, list):
            result.extend(step for step in steps if isinstance(step, dict))
    return result


def _step_uses(step: dict[Any, Any], action: str) -> bool:
    uses = step.get("uses")
    return isinstance(uses, str) and uses.startswith(action)


def _step_with(step: dict[Any, Any]) -> dict[Any, Any]:
    value = step.get("with", {})
    return value if isinstance(value, dict) else {}


def _retention_days(step: dict[Any, Any]) -> int | None:
    try:
        return int(str(_step_with(step).get("retention-days")))
    except (TypeError, ValueError):
        return None


def _content(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _normalized_shell_text(path: Path) -> str:
    """Normalize YAML shell blocks without weakening command requirements."""

    text = _content(path).replace("\\\n", " ")
    return " ".join(text.split())


def _uses_secret_context_in_if(path: Path) -> bool:
    text = _content(path)
    return "if: ${{ secrets." in text or "if:${{ secrets." in text


def _contains_git_push(path: Path) -> bool:
    return "git push" in _content(path)


def _has_durable_artifact(data: dict[Any, Any], *accepted_names: str) -> bool:
    for step in _iter_steps(data):
        if not _step_uses(step, "actions/upload-artifact@"):
            continue
        name = str(_step_with(step).get("name", ""))
        if not any(name == item or name.startswith(f"{item}-") for item in accepted_names):
            continue
        days = _retention_days(step)
        if days is not None and days >= 30:
            return True
    return False


def _has_durable_pages_artifact(data: dict[Any, Any]) -> bool:
    return any(
        _step_uses(step, "actions/upload-pages-artifact@")
        and (_retention_days(step) or 0) >= 30
        for step in _iter_steps(data)
    )


def _ci_contract(path: Path) -> list[str]:
    text = _content(path)
    errors: list[str] = []
    required = {
        "frontend-browser:": "missing required frontend-browser Playwright profile",
        "python -m playwright install --with-deps chromium": "missing Python Playwright Chromium install",
        "npx playwright install chromium": "missing Node Playwright Chromium install",
        "npm run test:frontend:browser": "missing canonical frontend browser profile",
        "npm run test:frontend:no-network": "missing same-origin frontend smoke",
        "python scripts/validate_bandit_suppressions.py --require-active": "missing Bandit suppression hygiene guard",
        "python scripts/validate_test_skips.py": "missing pytest skip governance guard",
        "python scripts/validate_capability_registry.py": "missing capability registry validator",
        "python scripts/validate_core_compatibility.py": "missing core compatibility validator",
        "python scripts/validate_module_ownership.py": "missing module ownership validator",
    }
    for token, message in required.items():
        if token not in text:
            errors.append(message)
    frontend_start = text.find("  frontend:")
    browser_start = text.find("  frontend-browser:")
    if frontend_start == -1 or browser_start == -1 or browser_start <= frontend_start:
        errors.append("frontend smoke job must precede frontend-browser job")
    else:
        frontend = text[frontend_start:browser_start]
        if "npx playwright install chromium" not in frontend:
            errors.append("frontend smoke job must install Node Playwright Chromium")
    bandit = text.find("bandit -r src/configstream scripts tools")
    suppression = text.find("python scripts/validate_bandit_suppressions.py --require-active")
    if bandit == -1 or suppression == -1 or bandit > suppression:
        errors.append("Bandit suppression guard must run after Bandit")
    skip_guard = text.find("python scripts/validate_test_skips.py")
    pytest_run = text.find("pytest -q")
    if skip_guard == -1 or pytest_run == -1 or skip_guard > pytest_run:
        errors.append("pytest skip governance guard must run before tests")
    return errors


def _release_contract(path: Path) -> bool:
    text = _content(path)
    return all(
        token in text
        for token in (
            "python scripts/validate_capability_registry.py",
            "python scripts/validate_core_compatibility.py",
            "python scripts/validate_module_ownership.py",
        )
    )


def _main_contract(path: Path, data: dict[Any, Any]) -> list[str]:
    text = _content(path)
    normalized = _normalized_shell_text(path)
    errors: list[str] = []
    if _contains_git_push(path):
        errors.append("main data workflow must not push commits")
    if "python scripts/dynamic_reshard.py" not in text or "source-reshard-recommendation" not in text:
        errors.append("dynamic resharding must publish an artifact recommendation")
    if not _has_durable_artifact(data, "pipeline-output"):
        errors.append("pipeline-output artifact retention must be durable")
    required_commands = (
        "cp -R frontend/. output/",
        "cp output/proxies.json output/api/proxies",
        "cp output/metadata.json output/api/stats",
        "python scripts/validate_pages_artifact.py --refresh-contract output",
        "python scripts/validate_pages_artifact.py --native-client-check",
    )
    if not all(" ".join(token.split()) in normalized for token in required_commands):
        errors.append("data release validation must prepare and validate the public output artifact")
    if "--native-report-file pipeline-evidence/native_client_check_report.json" not in normalized and "generate_evidence_bundle.py" not in text:
        errors.append("data release assets must use the shared output contract")
    jobs = data.get("jobs", {})
    merge = jobs.get("merge_results", {}) if isinstance(jobs, dict) else {}
    if isinstance(merge, dict):
        steps = merge.get("steps", [])
        downloads_wasm = any(
            isinstance(step, dict)
            and _step_uses(step, "actions/download-artifact@")
            and str(_step_with(step).get("name", "")).startswith("frontend-wasm")
            for step in steps
            if isinstance(steps, list)
        )
        needs = merge.get("needs", [])
        normalized_needs = (
            [needs]
            if isinstance(needs, str)
            else list(needs)
            if isinstance(needs, list)
            else []
        )
        if downloads_wasm and "build_wasm" not in [str(item) for item in normalized_needs]:
            errors.append("merge_results must depend on build_wasm when downloading frontend-wasm")
    return errors


def _deploy_pages_contract(path: Path, data: dict[Any, Any]) -> list[str]:
    text = _content(path)
    normalized = _normalized_shell_text(path)
    errors: list[str] = []
    sealed_required = (
        "release_manifest.json",
        "artifact_digests",
        "source_commit_sha",
        "expires_at",
        "gh run download",
        "python scripts/validate_pages_artifact.py --native-client-check output",
        "scripts/verify_pages_deployment.py",
        "steps.deployment.outputs.page_url",
    )
    if not all(" ".join(token.split()) in normalized for token in sealed_required):
        errors.append("Pages deploy must verify and deploy one exact sealed artifact")
    forbidden = ("npm run build", "vite build", "frontend-dist")
    if any(token in text for token in forbidden):
        errors.append("Pages deploy must not rebuild frontend assets")
    if not _has_durable_pages_artifact(data):
        errors.append("Pages artifact retention must be durable")
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
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{path}: YAML parse failed: {exc}")
            continue
        except OSError as exc:
            errors.append(f"{path}: could not read file: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path}: workflow root must be a YAML mapping")
            continue
        if "on" not in data and True not in data:
            errors.append(f"{path}: missing 'on' trigger")
        if not isinstance(data.get("jobs"), dict) or not data["jobs"]:
            errors.append(f"{path}: missing non-empty 'jobs' mapping")
        if path.name in CONCURRENCY_REQUIRED and "concurrency" not in data:
            errors.append(f"{path}: missing top-level concurrency policy")
        if _uses_secret_context_in_if(path):
            errors.append(f"{path}: secrets context must not be used directly in if expressions")
        for ref in sorted(UNRESOLVABLE_ACTION_REFS):
            if ref in _content(path):
                errors.append(f"{path}: unresolvable action reference: {ref}")
        if path.name == "ci.yml":
            errors.extend(f"{path}: {message}" for message in _ci_contract(path))
        elif path.name == "release.yml" and not _release_contract(path):
            errors.append(f"{path}: missing capability/core/module ownership contract validators")
        elif path.name == "main.yml":
            errors.extend(f"{path}: {message}" for message in _main_contract(path, data))
        elif path.name == "retest.yml" and not _has_durable_artifact(data, "pipeline-output", "retest-output"):
            errors.append(f"{path}: pipeline-output artifact retention must be durable")
        elif path.name == "deploy-pages.yml":
            errors.extend(f"{path}: {message}" for message in _deploy_pages_contract(path, data))
        if _contains_git_push(path):
            errors.append(f"{path}: workflows must not push directly to the repository")

    if errors:
        print("ERROR: workflow validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"OK: validated {len(workflow_files)} workflow files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
