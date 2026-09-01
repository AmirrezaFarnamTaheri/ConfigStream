# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_test_profile


def test_unit_commands_expand_root_tests_without_shell_globs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_root.py").write_text("def test_ok(): pass\n", encoding="utf-8")
    monkeypatch.setattr(run_test_profile, "REPO_ROOT", tmp_path)

    commands = run_test_profile._unit_commands("python")

    assert commands[0][0][-1] == "tests/unit"
    assert commands[1][0][-1] == "tests/test_root.py"
    assert all("*" not in argument for command, _ in commands for argument in command)


def test_unit_commands_skip_empty_root_test_glob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "tests").mkdir()
    monkeypatch.setattr(run_test_profile, "REPO_ROOT", tmp_path)

    commands = run_test_profile._unit_commands("python")

    assert len(commands) == 1


def test_frontend_browser_profile_disables_plugin_autoload_and_loads_required_plugins() -> (
    None
):
    commands = run_test_profile._frontend_browser_commands("python", "npm")

    pytest_command, environment = commands[0]

    assert environment == {
        "CONFIGSTREAM_REQUIRE_PLAYWRIGHT": "1",
        "ENVIRONMENT": "test",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    assert pytest_command[:6] == [
        "python",
        "-m",
        "pytest",
        "-q",
        "-p",
        "pytest_asyncio.plugin",
    ]
    assert pytest_command[6:10] == [
        "-p",
        "pytest_playwright.pytest_playwright",
        "-p",
        "pytest_base_url.plugin",
    ]
    assert pytest_command[-1] == "tests/e2e/test_frontend.py"


def test_frontend_browser_profile_scopes_optional_browser_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PLAYWRIGHT_BROWSER_CHANNEL", "msedge")

    commands = run_test_profile._frontend_browser_commands("python", "npm")

    pytest_command, _ = commands[0]
    assert "--browser-channel=msedge" in pytest_command
