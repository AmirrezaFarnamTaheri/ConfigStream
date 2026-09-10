# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def test_legacy_tester_is_not_release_authority() -> None:
    runtime = json.loads(
        Path("config/runtime-versions.json").read_text(encoding="utf-8")
    )
    sing_box = runtime["sing_box"]

    assert sing_box["embedded_tester"] != sing_box["release_validator"]
    assert sing_box["release_authority"] == "native-validator-only"
    assert "pre-release-connectivity-screen-only" in sing_box["embedded_contract"]
    assert "release-validator conformance" in sing_box["embedded_contract"]


def test_release_artifacts_are_checked_by_governed_native_sing_box() -> None:
    native_checks = Path("scripts/native_client_checks.py").read_text(encoding="utf-8")
    workflow = yaml.safe_load(Path(".github/workflows/main.yml").read_text(encoding="utf-8"))
    runtime = json.loads(
        Path("config/runtime-versions.json").read_text(encoding="utf-8")
    )

    assert '[str(singbox_binary), "check", "-c", str(path)]' in native_checks
    assert isinstance(workflow, dict)
    env = workflow.get("env")
    assert isinstance(env, dict)
    assert str(env.get("SING_BOX_VERSION")) == runtime["sing_box"]["release_validator"]

    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    executable_steps: list[dict[str, Any]] = []
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        executable_steps.extend(
            step
            for step in steps
            if isinstance(step, dict)
            and "native_client_checks.py" in str(step.get("run") or "")
        )

    assert len(executable_steps) == 1
    command = str(executable_steps[0]["run"])
    assert "python scripts/native_client_checks.py output" in command
    assert "pipeline-evidence/native_client_check_report.json" in command
