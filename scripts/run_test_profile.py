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


def _unit_commands(python: str) -> list[tuple[list[str], dict[str, str] | None]]:
    """Build portable unit commands without relying on shell glob expansion."""

    environment = {"ENVIRONMENT": "test"}
    commands: list[tuple[list[str], dict[str, str] | None]] = [
        ([python, "-m", "pytest", "-q", "tests/unit"], environment)
    ]
    root_tests = sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "tests").glob("test_*.py")
    )
    if root_tests:
        commands.append(([python, "-m", "pytest", "-q", *root_tests], environment))
    return commands


def _frontend_browser_commands(
    python: str, npm: str
) -> list[tuple[list[str], dict[str, str] | None]]:
    """Run browser tests without inheriting unrelated host pytest plugins."""

    pytest_environment = {
        "CONFIGSTREAM_REQUIRE_PLAYWRIGHT": "1",
        "ENVIRONMENT": "test",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    pytest_command = [
        python,
        "-m",
        "pytest",
        "-q",
        "-p",
        "pytest_asyncio.plugin",
        "-p",
        "pytest_playwright.pytest_playwright",
        "-p",
        "pytest_base_url.plugin",
    ]
    browser_channel = os.environ.get("PLAYWRIGHT_BROWSER_CHANNEL", "").strip()
    if browser_channel:
        pytest_command.append(f"--browser-channel={browser_channel}")
    pytest_command.extend(
        [
            "tests/e2e/test_frontend.py",
            "tests/e2e/test_frontend_visual.py",
            "tests/e2e/test_laboratory_ui.py",
        ]
    )
    return [
        (pytest_command, pytest_environment),
        ([npm, "run", "test:frontend:no-network"], None),
        ([npm, "run", "test:frontend:degraded"], None),
    ]


def run_profile(profile: str) -> int:
    python = sys.executable
    npm = shutil.which("npm") or "npm"

    profiles: dict[str, list[tuple[list[str], dict[str, str] | None]]] = {
        "unit": _unit_commands(python),
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
                    "tests/e2e/test_pipeline_shards_light.py",
                ],
                {"ENVIRONMENT": "test"},
            )
        ],
        "frontend-browser": _frontend_browser_commands(python, npm),
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
