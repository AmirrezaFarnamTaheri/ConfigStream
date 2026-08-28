# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression coverage for the Pages workflow-run deployment contract."""

from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "deploy-pages.yml"
)


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_retest_noop_is_qualified_before_pages_deploy() -> None:
    workflow = _workflow_text()

    assert "  candidate:\n" in workflow
    assert (
        'source_name=$(gh api "repos/${REPOSITORY}/actions/runs/${selected}"'
        in workflow
    )
    assert '[ "$EVENT_NAME" = workflow_run ] && [ "$source_name" = Retest ]' in workflow
    assert 'echo "has_candidate=false" >> "$GITHUB_OUTPUT"' in workflow
    assert "    needs: candidate\n" in workflow
    assert "needs.candidate.outputs.has_candidate == 'true'" in workflow


def test_non_retest_missing_artifact_still_fails_closed() -> None:
    workflow = _workflow_text()

    assert (
        "Approved deployment source $selected did not publish pipeline-output"
        in workflow
    )
    assert "Deployment disposition" in workflow
    assert 'raise SystemExit("Pages deployment failed closed")' in workflow
