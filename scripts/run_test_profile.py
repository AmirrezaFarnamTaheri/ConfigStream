# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run named ConfigStream validation profiles.

Profiles make skipped browser coverage explicit instead of burying it inside a
large all-tests run.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], *, env: dict[str, str] | None = None) -> int:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    print("+ " + " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=REPO_ROOT, env=merged_env)  # nosec B603
    return int(completed.returncode)


def _npm() -> str:
    npm = shutil.which("npm")
    if not npm:
        raise FileNotFoundError("npm was not found on PATH")
    return npm


def _run_many(commands: list[tuple[list[str], dict[str, str] | None]]) -> int:
    for command, env in commands:
        code = _run(command, env=env)
        if code != 0:
            return code
    return 0


def run_profile(profile: str) -> int:
    python = sys.executable
    npm = shutil.which("npm") or "npm"

    profiles: dict[str, list[tuple[list[str], dict[str, str] | None]]] = {
        "unit": [
            ([python, "-m", "pytest", "-q", "tests/unit"], {"ENVIRONMENT": "test"}),
            (
                [python, "-m", "pytest", "-q", "tests/test_*.py"],
                {"ENVIRONMENT": "test"},
            ),
        ],
        "integration": [
            (
                [
                    python,
                    "-m",
                    "pytest",
                    "-q",
                    "tests/scenarios",
                    "tests/fuzz",
                    "tests/e2e/test_failure_scenarios.py",
                    "tests/e2e/test_mixed_protocols.py",
                    "tests/e2e/test_pipeline_real.py",
                ],
                {"ENVIRONMENT": "test"},
            )
        ],
        "frontend-browser": [
            (
                [python, "-m", "pytest", "-q", "tests/e2e/test_frontend.py"],
                {"CONFIGSTREAM_REQUIRE_PLAYWRIGHT": "1", "ENVIRONMENT": "test"},
            ),
            ([npm, "run", "test:frontend:no-network"], None),
            ([npm, "run", "test:frontend:degraded"], None),
        ],
    }

    if profile not in profiles:
        print(f"Unknown profile: {profile}", file=sys.stderr)
        return 2
    return _run_many(profiles[profile])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "profile",
        choices=("unit", "integration", "frontend-browser"),
        help="Validation profile to run.",
    )
    args = parser.parse_args(argv)
    return run_profile(args.profile)


if __name__ == "__main__":
    raise SystemExit(main())
