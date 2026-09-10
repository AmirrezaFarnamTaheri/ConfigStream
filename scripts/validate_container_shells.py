# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reject Bash-only run syntax executed with a job container's default /bin/sh."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
BASH_ONLY_RUN_MARKERS = (
    "set -o pipefail",
    "set -euo pipefail",
    "${PIPESTATUS[",
    "[[ ",
    "shopt ",
    "declare -a ",
    "source ",
    "<( ",
)


def _uses_bash(value: object) -> bool:
    return isinstance(value, str) and "bash" in value.lower()


def validate_workflow(data: dict[Any, Any]) -> list[str]:
    """Return container-shell contract violations in one parsed workflow."""

    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict):
        return []
    errors: list[str] = []
    for job_name, raw_job in jobs.items():
        if not isinstance(raw_job, dict) or "container" not in raw_job:
            continue
        defaults = raw_job.get("defaults", {})
        run_defaults = defaults.get("run", {}) if isinstance(defaults, dict) else {}
        default_shell = (
            run_defaults.get("shell") if isinstance(run_defaults, dict) else None
        )
        steps = raw_job.get("steps", [])
        if not isinstance(steps, list):
            continue
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                continue
            command = step.get("run")
            if not isinstance(command, str):
                continue
            if not any(marker in command for marker in BASH_ONLY_RUN_MARKERS):
                continue
            effective_shell = step.get("shell", default_shell)
            if _uses_bash(effective_shell):
                continue
            label = step.get("name") or f"step {index}"
            errors.append(
                f"container job {job_name!s} step {label!r} uses Bash-only syntax "
                "without an explicit Bash shell"
            )
    return errors


def main() -> int:
    errors: list[str] = []
    for path in sorted(WORKFLOW_DIR.glob("*.y*ml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"{path}: cannot parse workflow: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path}: workflow root must be a mapping")
            continue
        errors.extend(f"{path}: {error}" for error in validate_workflow(data))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: job-container shell contracts validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
