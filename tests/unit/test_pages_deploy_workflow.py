# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression coverage for the Pages workflow-run deployment contract."""

import json
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
    assert "gh api \"repos/${REPOSITORY}/branches/main\" --jq '.commit.sha'" in workflow
    assert 'if [ "$current_main" != "$EXPECTED_SOURCE_SHA" ]; then' in workflow
    assert "--name source-freshness" in workflow
    assert "--required-stage source-freshness" in workflow


def test_pages_candidate_verification_avoids_nested_heredoc() -> None:
    workflow = _workflow_text()
    verification = workflow.split("--name verify-sealed-pages-artifact", 1)[1].split(
        "- name: Snapshot current verified Pages release", 1
    )[0]

    assert (
        "python scripts/validate_pages_artifact.py output "
        '--expected-source-sha "$EXPECTED_SOURCE_SHA"' in verification
    )
    assert 'python - <<"PY"' not in verification


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
    assert "VARIABLE_ALLOW_UNSIGNED_PAGES: ${{ vars.ALLOW_UNSIGNED_PAGES }}" in workflow
    assert "Resolve Pages unsigned trust policy" in workflow
    assert "python scripts/pages_trust_policy.py" in workflow
    policy = json.loads(
        (WORKFLOW.parents[2] / "config" / "pages-trust-policy.json").read_text(
            encoding="utf-8"
        )
    )
    assert policy["repository"] == "AmirrezaFarnamTaheri/ConfigStream"
    assert policy["allow_unsigned_pages"] is False
    assert workflow.count('signature_policy_args+=(--public-key "$CS_PUBLIC_KEY")') >= 4
    assert workflow.count("signature_policy_args+=(--allow-unsigned)") >= 4

    snapshot = workflow.split("- name: Snapshot current verified Pages release", 1)[
        1
    ].split("- name: Record last-known-good availability", 1)[0]
    rollback = workflow.split("- name: Verify rollback restoration", 1)[1].split(
        "- name: Record rollback action outcomes", 1
    )[0]
    assert "verify_args+=(--allow-unsigned)" not in snapshot
    assert "verify_args+=(--allow-unsigned)" in rollback
