# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"


def _default_run_shell(node: dict[str, Any]) -> str:
    defaults = node.get("defaults")
    if not isinstance(defaults, dict):
        return ""
    run_defaults = defaults.get("run")
    if not isinstance(run_defaults, dict):
        return ""
    return str(run_defaults.get("shell") or "").strip()


def _is_bash(shell: str) -> bool:
    return bool(shell) and shell.split(maxsplit=1)[0] == "bash"


def test_container_run_steps_resolve_to_bash() -> None:
    """Container jobs default to ``sh``; Bash-dependent steps must pin Bash."""

    failures: list[str] = []
    for workflow_path in sorted(WORKFLOW_DIR.glob("*.y*ml")):
        payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            continue
        workflow_shell = _default_run_shell(payload)
        jobs = payload.get("jobs")
        if not isinstance(jobs, dict):
            continue
        for job_name, raw_job in jobs.items():
            if not isinstance(raw_job, dict) or "container" not in raw_job:
                continue
            job_shell = _default_run_shell(raw_job) or workflow_shell
            steps = raw_job.get("steps")
            if not isinstance(steps, list):
                continue
            for index, raw_step in enumerate(steps, start=1):
                if not isinstance(raw_step, dict) or "run" not in raw_step:
                    continue
                shell = str(raw_step.get("shell") or job_shell).strip()
                if _is_bash(shell):
                    continue
                step_name = str(raw_step.get("name") or f"step-{index}")
                failures.append(
                    f"{workflow_path.name}:{job_name}:{step_name} resolves to "
                    f"{shell or 'container-default-sh'} instead of bash"
                )

    assert not failures, "\n".join(failures)
