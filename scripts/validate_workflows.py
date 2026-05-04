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
        if _contains_git_push(path):
            missing_ignores = SOURCE_RESHARD_PATHS - _push_paths_ignore(data)
            if missing_ignores:
                missing = ", ".join(sorted(missing_ignores))
                errors.append(
                    f"{path}: git push workflow must ignore source reshard paths: "
                    f"{missing}"
                )

    if errors:
        print("ERROR: workflow validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"OK: validated {len(workflow_files)} workflow files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
