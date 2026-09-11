# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/deploy-pages.yml"


def _workflow() -> dict[Any, Any]:
    loaded = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _deploy_steps() -> list[dict[str, Any]]:
    workflow = _workflow()
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    deploy = jobs.get("deploy")
    assert isinstance(deploy, dict)
    steps = deploy.get("steps")
    assert isinstance(steps, list)
    return [step for step in steps if isinstance(step, dict)]


def test_pages_deployment_requires_rollback_baseline() -> None:
    steps = _deploy_steps()
    by_name = {str(step.get("name")): step for step in steps if step.get("name")}

    gate = by_name["Require rollback baseline before production mutation"]
    gate_run = str(gate.get("run") or "")
    assert 'echo "ROLLBACK_READY=true" >> "$GITHUB_ENV"' in gate_run
    assert "--name rollback-baseline --status failed" in gate_run
    assert 'echo "DEPLOY_READY=false" >> "$GITHUB_ENV"' in gate_run

    upload = by_name["Upload sealed Pages artifact"]
    deploy = by_name["Deploy to GitHub Pages"]
    assert "env.DEPLOY_READY == 'true'" in str(upload.get("if") or "")
    assert "env.ROLLBACK_READY == 'true'" in str(upload.get("if") or "")
    assert "env.DEPLOY_READY == 'true'" in str(deploy.get("if") or "")
    assert "env.ROLLBACK_READY == 'true'" in str(deploy.get("if") or "")

    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "--required-stage rollback-baseline" in workflow_text


def test_pages_bootstrap_exception_is_explicit_manual_input_only() -> None:
    workflow = _workflow()
    triggers = workflow.get("on") or workflow.get(True)
    assert isinstance(triggers, dict)
    dispatch = triggers.get("workflow_dispatch")
    assert isinstance(dispatch, dict)
    inputs = dispatch.get("inputs")
    assert isinstance(inputs, dict)
    bootstrap = inputs.get("allow_bootstrap_without_lkg")
    assert isinstance(bootstrap, dict)
    assert bootstrap.get("default") is False
    assert bootstrap.get("required") is False

    steps = _deploy_steps()
    gate = next(
        step
        for step in steps
        if step.get("name") == "Require rollback baseline before production mutation"
    )
    env = gate.get("env")
    assert isinstance(env, dict)
    expression = str(env.get("ALLOW_BOOTSTRAP_WITHOUT_LKG") or "")
    assert "github.event_name == 'workflow_dispatch'" in expression
    assert "inputs.allow_bootstrap_without_lkg" in expression
    assert "workflow_run" not in expression
    assert "Explicit manual bootstrap approved without a rollback baseline" in str(
        gate.get("run") or ""
    )
