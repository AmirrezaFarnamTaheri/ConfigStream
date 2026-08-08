# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_xray_pipeline_capability_matches_stable_output_contract():
    registry = json.loads(
        (ROOT / "docs/capability_registry.json").read_text(encoding="utf-8")
    )
    capability = next(
        item
        for item in registry["capabilities"]
        if item["id"] == "cap.core.xray_pipeline_export"
    )
    assert capability["status"] == "stable"
    assert "xray.json" in capability["outputs"]
    assert capability["implementation"]
    assert capability["tests"]


def test_triage_report_does_not_cache_live_issue_or_pr_counts():
    text = (ROOT / "TRIAGE_REPORT.md").read_text(encoding="utf-8")
    assert "$(date" not in text
    assert "Open Issues" not in text
    assert "Dependabot PRs" not in text
    assert "intentionally not cached" in text


def test_triage_report_uses_canonical_readiness_keys():
    readiness = json.loads((ROOT / "docs/readiness.json").read_text(encoding="utf-8"))
    text = (ROOT / "TRIAGE_REPORT.md").read_text(encoding="utf-8")

    assert f"Version: `{readiness['project_version']}`" in text
    assert f"Readiness: `{readiness['verdict']}`" in text
    assert f"Production ready: `{readiness['production_ready']}`" in text


def test_triage_report_uses_exact_debt_ratchets():
    exceptions = json.loads(
        (ROOT / "config/exception-boundary-budget.json").read_text(encoding="utf-8")
    )
    functions = json.loads(
        (ROOT / "config/function-size-budget.json").read_text(encoding="utf-8")
    )
    text = (ROOT / "TRIAGE_REPORT.md").read_text(encoding="utf-8")

    assert (
        f"Exact broad exception boundaries: **{exceptions['total_ceiling']}**" in text
    )
    assert (
        f"Oversized functions (300+ lines): **{len(functions['functions'])}**" in text
    )
