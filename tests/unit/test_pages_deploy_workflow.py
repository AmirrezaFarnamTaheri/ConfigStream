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


def test_pages_rechecks_current_main_before_publication() -> None:
    workflow = _workflow_text()

    freshness = workflow.index(
        "Require source run to remain current main before publication"
    )
    upload = workflow.index("Upload sealed Pages artifact")
    assert freshness < upload
    assert 'gh api "repos/${REPOSITORY}/branches/main" --jq \'.commit.sha\'' in workflow
    assert 'if [ "$current_main" != "$EXPECTED_SOURCE_SHA" ]; then' in workflow
    assert "--name source-freshness" in workflow
    assert "--required-stage source-freshness" in workflow


def test_rollback_requires_an_attempted_pages_deployment() -> None:
    workflow = _workflow_text()
    attempted = (
        "steps.deployment.outcome == 'success' || "
        "steps.deployment.outcome == 'failure'"
    )

    assert workflow.count(attempted) >= 2
    assert "Restore last-known-good Pages release" in workflow
    assert "Verify rollback restoration" in workflow


def test_pages_signature_policy_is_explicit_at_every_trust_boundary() -> None:
    workflow = _workflow_text()

    assert workflow.count("CS_PUBLIC_KEY: ${{ secrets.CS_PUBLIC_KEY }}") >= 4
    assert (
        workflow.count(
            "ALLOW_UNSIGNED_PAGES: ${{ vars.ALLOW_UNSIGNED_PAGES || 'false' }}"
        )
        >= 4
    )
    assert workflow.count("signature_policy_args+=(--public-key \"$CS_PUBLIC_KEY\")") >= 4
    assert workflow.count("signature_policy_args+=(--allow-unsigned)") >= 4
