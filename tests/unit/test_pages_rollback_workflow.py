# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/deploy-pages.yml"


def test_pages_workflow_snapshots_and_restores_last_known_good() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Snapshot current verified Pages release" in workflow
    assert "scripts/snapshot_pages_release.py" in workflow
    assert "-c requirements-prod.txt" in workflow
    assert "httpx cryptography pydantic pydantic-settings PyYAML" in workflow
    assert "CS_PUBLIC_KEY: ${{ secrets.CS_PUBLIC_KEY }}" in workflow
    assert "PYTHONPATH: src" in workflow
    assert "Upload last-known-good rollback artifact" in workflow
    assert "Restore last-known-good Pages release" in workflow
    assert "Verify rollback restoration" in workflow
    assert "env.SMOKE_OK != 'true'" in workflow
    assert "last-known-good" in workflow
    assert "name: github-pages-candidate" in workflow
    assert "artifact_name: github-pages-candidate" in workflow
    assert "name: github-pages-last-known-good" in workflow
    assert "artifact_name: github-pages-last-known-good" in workflow


def test_pages_workflow_requires_verified_rollback_baseline_before_deploy() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "allow_bootstrap_without_lkg" in workflow
    assert "Require rollback baseline before production mutation" in workflow
    assert "ROLLBACK_READY=false" in workflow
    assert "ROLLBACK_READY=true" in workflow
    assert "--required-stage rollback-baseline" in workflow
    assert "env.DEPLOY_READY == 'true' && env.ROLLBACK_READY == 'true'" in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert "inputs.allow_bootstrap_without_lkg" in workflow
