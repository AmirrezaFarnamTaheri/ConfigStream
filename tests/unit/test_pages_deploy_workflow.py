# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression coverage for the Pages workflow-run deployment contract."""

from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "deploy-pages.yml"
)


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_pages_accepts_only_canonical_configstream_runs() -> None:
    workflow = _workflow_text()

    assert 'workflows: ["Config\'s Stream"]' in workflow
    assert 'allowed_workflows = {"Config\'s Stream"}' in workflow
    assert 'workflows: ["Config\'s Stream", "Retest"]' not in workflow
    assert 'allowed_workflows = {"Config\'s Stream", "Retest"}' not in workflow
    assert "Retest" not in workflow


def test_missing_canonical_artifact_fails_closed() -> None:
    workflow = _workflow_text()

    assert "  candidate:\n" in workflow
    assert 'echo "has_candidate=false" >> "$GITHUB_OUTPUT"' in workflow
    assert (
        "Approved deployment source $selected did not publish pipeline-output"
        in workflow
    )
    assert "    needs: candidate\n" in workflow
    assert "needs.candidate.outputs.has_candidate == 'true'" in workflow
    assert "Deployment disposition" in workflow
    assert 'raise SystemExit("Pages deployment failed closed")' in workflow
