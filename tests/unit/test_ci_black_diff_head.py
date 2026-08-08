# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for the pull-request Black diff boundary."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def test_pr_black_diffs_against_pull_request_head_not_merge_commit() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert (
        "HEAD_SHA: ${{ github.event.pull_request.head.sha || github.sha }}" in workflow
    )
    assert "HEAD_SHA: ${{ github.sha }}" not in workflow
