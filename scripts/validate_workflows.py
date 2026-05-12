# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate GitHub Actions workflow YAML files."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

WORKFLOW_DIR = Path(".github") / "workflows"
SOURCE_RESHARD_PATHS = {"sources/batch_*.txt", "sources/backup_dynamic/**"}
CONCURRENCY_REQUIRED = {
    "main.yml",
    "retest.yml",
    "deploy-pages.yml",
    "deploy_mirror.yml",
}


def _trigger_block(data: dict[Any, Any]) -> Any:
    return data.get("on", data.get(True))


def _push_paths_ignore(data: dict[Any, Any]) -> set[str]:
    triggers = _trigger_block(data)
    if not isinstance(triggers, dict):
        return set()
    push = triggers.get("push")
    if not isinstance(push, dict):
        return set()
    paths_ignore = push.get("paths-ignore", [])
    if not isinstance(paths_ignore, list):
        return set()
    return {str(path) for path in paths_ignore}


def _contains_git_push(path: Path) -> bool:
    try:
        return "git push" in path.read_text(encoding="utf-8")
    except OSError:
        return False


def _main_has_durable_pipeline_output(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return (
        "name: pipeline-output" in content
        and "retention-days: 30" in content
    )


def _main_publishes_reshard_recommendation(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return (
        "python scripts/dynamic_reshard.py" in content
        and "name: source-reshard-recommendation" in content
        and "git push origin HEAD" not in content
    )


def _main_release_assets_use_output_contract(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return (
        "python scripts/validate_pages_artifact.py output" in content
        and "Ensure release assets are non-empty" not in content
        and "test -s output/base64.txt" not in content
        and "echo \"# FAILED GENERATION\"" not in content
    )


def _deploy_pages_has_frontend_placeholder_guard(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return (
        "scripts/validate_frontend_placeholders.py --inject-env --strict output"
        in content
        and "CS_PUBLIC_KEY: ${{ secrets.CS_PUBLIC_KEY }}" in content
        and "STEGO_KEY: ${{ secrets.STEGO_KEY }}" in content
    )


def _deploy_pages_uses_canonical_raw_frontend(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return (
        "cp -R frontend/. output/" in content
        and "frontend-dist" not in content
        and "npm run build" not in content
        and "vite build" not in content
    )


def _deploy_pages_has_public_smoke(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return (
        "scripts/verify_pages_deployment.py" in content
        and "steps.deployment.outputs.page_url" in content
    )


def _ci_has_required_frontend_browser_profile(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return (
        "frontend-browser:" in content
        and "python -m playwright install --with-deps chromium" in content
        and "npm run test:frontend:browser" in content
    )


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
        # PyYAML's YAML 1.1 resolver parses the unquoted GitHub Actions key
        # `on` as boolean True. Accept both shapes while still requiring the
        # workflow trigger key to be present.
        if "on" not in data and True not in data:
            errors.append(f"{path}: missing 'on' trigger")
        if not isinstance(data.get("jobs"), dict) or not data["jobs"]:
            errors.append(f"{path}: missing non-empty 'jobs' mapping")
        if path.name in CONCURRENCY_REQUIRED and "concurrency" not in data:
            errors.append(f"{path}: missing top-level concurrency policy")
        if (
            path.name == "deploy-pages.yml"
            and not _deploy_pages_has_frontend_placeholder_guard(path)
        ):
            errors.append(
                f"{path}: missing frontend placeholder injection/validation guard"
            )
        if path.name == "deploy-pages.yml" and not _deploy_pages_uses_canonical_raw_frontend(
            path
        ):
            errors.append(
                f"{path}: Pages deploy must use canonical raw static frontend"
            )
        if path.name == "deploy-pages.yml" and not _deploy_pages_has_public_smoke(path):
            errors.append(f"{path}: missing deployed Pages URL smoke")
        if path.name == "ci.yml" and not _ci_has_required_frontend_browser_profile(
            path
        ):
            errors.append(
                f"{path}: missing required frontend-browser Playwright profile"
            )
        if path.name == "main.yml" and _contains_git_push(path):
            errors.append(f"{path}: main data workflow must not push commits")
        if path.name == "main.yml" and not _main_publishes_reshard_recommendation(
            path
        ):
            errors.append(
                f"{path}: dynamic resharding must publish an artifact recommendation"
            )
        if path.name == "main.yml" and not _main_has_durable_pipeline_output(path):
            errors.append(
                f"{path}: pipeline-output artifact retention must be durable"
            )
        if path.name == "main.yml" and not _main_release_assets_use_output_contract(
            path
        ):
            errors.append(
                f"{path}: data release assets must use the shared output contract"
            )
        if path.name == "main.yml" and not _main_publishes_reshard_recommendation(
            path
        ):
            errors.append(
                f"{path}: source resharding must publish recommendations "
                "instead of pushing source mutations"
            )
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
