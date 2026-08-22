#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate a non-stale local remediation report from repository evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "TRIAGE_REPORT.md"


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain an object")
    return value


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def render() -> str:
    readiness = _load(ROOT / "docs/readiness.json")
    debt = _load(ROOT / "docs/debt_matrix.json")
    admission = _load(ROOT / "src/configstream/data/source-admission.json")
    exception_budget = _load(ROOT / "config/exception-boundary-budget.json")
    function_budget = _load(ROOT / "config/function-size-budget.json")
    summary = debt.get("summary", {})
    oversized_functions = function_budget.get("functions", {})
    if not isinstance(oversized_functions, dict):
        oversized_functions = {}
    lines = [
        "# ConfigStream Local Triage and Remediation State",
        "",
        "> Generated from checked-in repository evidence. Live GitHub issue and pull-request",
        "> counts are intentionally not cached here; query GitHub when that state is needed.",
        "",
        "## Release state",
        "",
        f"- Version: `{readiness.get('project_version', 'unknown')}`",
        f"- Readiness: `{readiness.get('verdict', 'unknown')}`",
        f"- Production ready: `{bool(readiness.get('production_ready', False))}`",
        "",
        "## Measured debt",
        "",
        f"- Total entries: **{summary.get('total', 0)}**",
        f"- Exact broad exception boundaries: **{exception_budget.get('total_ceiling', 0)}**",
        f"- Oversized functions (300+ lines): **{len(oversized_functions)}**",
        "",
        "## Source admission",
        "",
        f"- Admitted fetch locators: **{admission.get('entry_count', 0)}**",
        f"- Source-set digest: `{admission.get('source_set_sha256', 'unknown')}`",
        "",
        "## Live control-plane boundary",
        "",
        "Issue status, Dependabot state, branch protection, Actions results, and deployment",
        "state must be read from GitHub or the deployment provider. This file does not claim",
        "those mutable facts.",
    ]
    return "\n".join(lines) + "\n"


def is_current(expected: str) -> bool:
    if not OUTPUT.exists():
        return False
    return _normalize_newlines(OUTPUT.read_text(encoding="utf-8")) == expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not is_current(expected):
            print("TRIAGE_REPORT.md is stale", file=sys.stderr)
            return 1
        print("TRIAGE_REPORT.md is current")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8", newline="\n")
    print("wrote TRIAGE_REPORT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
