# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path


def test_pages_deployment_requires_rollback_baseline() -> None:
    workflow = Path(".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")

    assert "allow_bootstrap_without_lkg:" in workflow
    assert 'echo "ROLLBACK_READY=false" >> "$GITHUB_ENV"' in workflow
    assert "name: Require rollback baseline before production mutation" in workflow
    assert "--name rollback-baseline --status failed" in workflow
    assert 'echo "DEPLOY_READY=false" >> "$GITHUB_ENV"' in workflow
    assert "env.DEPLOY_READY == 'true' && env.ROLLBACK_READY == 'true'" in workflow
    assert "--required-stage rollback-baseline" in workflow


def test_pages_bootstrap_exception_is_explicit_manual_input_only() -> None:
    workflow = Path(".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")

    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert "inputs.allow_bootstrap_without_lkg" in workflow
    assert "Explicit manual bootstrap approved without a rollback baseline" in workflow
