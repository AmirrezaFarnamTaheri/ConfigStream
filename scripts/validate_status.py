# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate that STATUS.md stays aligned with remediation evidence."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ENCODING = "utf-8"
ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "STATUS.md"
PYPROJECT_PATH = ROOT / "pyproject.toml"


REQUIRED_PHRASES = [
    "Remediation in progress",
    "Not production-ready",
    "ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md",
    "Browser skip visibility",
    "CONFIGSTREAM_REQUIRE_PLAYWRIGHT=1",
]

FORBIDDEN_PHRASES = [
    "Production-ready",
    "production ready",
    "all workflows green",
    "811 passed",
    "823 passed",
    "899 passed",
    "dns_prewarm.py, fetcher.py, output.py",
    "Development Status :: 5 - Production/Stable",
]


def _read(path: Path) -> str:
    return path.read_text(encoding=ENCODING)


def _latest_full_pytest_count(status: str) -> int | None:
    matches = re.findall(r"`python -m pytest -q`: (\d+) passed, \d+ skipped", status)
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

    if "Development Status :: 4 - Beta" not in pyproject:
        errors.append("pyproject.toml must remain Beta while remediation is active")

    full_count = _latest_full_pytest_count(status)
    if full_count is None:
        errors.append("STATUS.md missing full pytest validation snapshot")
    elif full_count < 900:
        errors.append("STATUS.md full pytest count is stale or unexpectedly low")

    return errors


def main() -> None:
    errors = validate_status()
    if errors:
        print("ERROR: STATUS.md validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: STATUS.md remediation status validated.")


if __name__ == "__main__":
    main()
