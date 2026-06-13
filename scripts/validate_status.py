# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate that STATUS.md stays aligned with production-readiness evidence."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ENCODING = "utf-8"
ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "STATUS.md"
PYPROJECT_PATH = ROOT / "pyproject.toml"


REQUIRED_PHRASES = [
    "Repository production-ready",
    "v3.1.0",
    "Live Pages deployment currently fails smoke",
    "ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md",
    "Historical source-of-truth ledgers were fully absorbed into the master report and removed",
    "Absorbed Archive Value",
    "Closed Audit Items",
    "Validation Snapshot",
]

FORBIDDEN_PHRASES = [
    "Remediation in progress",
    "Not production-ready",
    "not production-ready",
    "all workflows green",
    "811 passed",
    "823 passed",
    "899 passed",
    "1012 passed",
    "1016 passed",
    "1018 passed",
    "1032 passed",
    "dns_prewarm.py, fetcher.py, output.py",
    "Development Status :: 4 - Beta",
    "The active current source of truth is [docs/history/source-of-truth/",
    "Historical ledgers under `docs/history/source-of-truth/` are archived evidence only",
    "Flip the gitleaks step to blocking",
    "remove `continue-on-error`",
    "105" "4 passed" ", 4 skipped",
    "pending after the 2026-06-13 " "frontend/governance refresh",
]


def _read(path: Path) -> str:
    return path.read_text(encoding=ENCODING)


def _latest_full_pytest_count(status: str) -> int | None:
    matches = re.findall(
        r"`python -m pytest -q`: (\d+) passed(?:, \d+ skipped)?", status
    )
    if not matches:
        return None
    return int(matches[-1])


def validate_status() -> list[str]:
    errors: list[str] = []
    status = _read(STATUS_PATH)
    pyproject = _read(PYPROJECT_PATH)

    for phrase in REQUIRED_PHRASES:
        if phrase not in status:
            errors.append(f"STATUS.md missing required phrase: {phrase}")

    for phrase in FORBIDDEN_PHRASES:
        if phrase in status:
            errors.append(f"STATUS.md contains stale/overconfident phrase: {phrase}")

    if "Development Status :: 5 - Production/Stable" not in pyproject:
        errors.append("pyproject.toml must be Production/Stable after closure")

    full_count = _latest_full_pytest_count(status)
    if full_count is None:
        errors.append("STATUS.md missing full pytest validation snapshot")
    elif full_count is not None and full_count < 1000:
        errors.append("STATUS.md full pytest count is stale or unexpectedly low")

    return errors


def main() -> None:
    errors = validate_status()
    if errors:
        print("ERROR: STATUS.md validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: STATUS.md production status validated.")


if __name__ == "__main__":
    main()
