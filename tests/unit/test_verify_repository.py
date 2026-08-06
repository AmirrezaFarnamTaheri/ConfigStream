# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from scripts import verify_repository


def test_static_verification_plan_includes_new_contracts() -> None:
    names = [stage.name for stage in verify_repository.build_plan("static")]
    assert "action-pins" in names
    assert "changelog" in names
    assert "runtime-versions" in names
    assert "environment-catalog" in names
    assert "status" in names
    assert "python-compile" in names


def test_stage_result_json_is_stable() -> None:
    result = verify_repository.StageResult(
        name="example",
        command=("python", "-V"),
        status="success",
        exit_code=0,
        duration_seconds=0.1,
        output="Python",
    )
    payload = result.to_dict()
    assert payload["name"] == "example"
    assert payload["command"] == ["python", "-V"]
    assert json.loads(json.dumps(payload))["status"] == "success"


def test_repository_static_verification_report_can_be_generated(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    outcome = verify_repository.verify(
        Path("."), profile="static", report_path=report, stop_on_failure=False
    )
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["profile"] == "static"
    assert payload["summary"]["failed"] == 0
    assert outcome is True


def test_full_verification_plan_uses_module_workdirs_for_native_checks() -> None:
    stages = {stage.name: stage for stage in verify_repository.build_plan("full")}
    assert stages["go-tester-race"].workdir == "src/go/tester"
    assert stages["go-utls-fuzz"].workdir == "src/go/utls_client"
    assert stages["rust-test"].workdir == "src/rust/ss_checker"
    assert "-bench=." in stages["go-tester-benchmark"].command


def test_frontend_stages_require_installed_locked_tools() -> None:
    stages = {stage.name: stage for stage in verify_repository.build_plan("full")}
    assert "node_modules/.bin/vite" in stages["frontend-build"].required_paths
    assert "node_modules/.bin/playwright" in stages["frontend-browser"].required_paths


def test_full_plan_declares_environment_preconditions() -> None:
    stages = {stage.name: stage for stage in verify_repository.build_plan("full")}
    assert "aiohttp_socks" in stages["python-unit"].required_python_modules
    assert stages["go-tester-unit"].minimum_tool_version == (1, 24, 0)
    assert stages["go-utls-unit"].minimum_tool_version == (1, 24, 3)


def test_extended_plan_is_the_full_only_tail() -> None:
    release = verify_repository.build_plan("release")
    extended = verify_repository.build_plan("extended")
    full = verify_repository.build_plan("full")
    assert full == release + extended


def test_all_verification_profiles_have_unique_stage_names() -> None:
    for profile in ("static", "release", "extended", "full"):
        names = [stage.name for stage in verify_repository.build_plan(profile)]
        assert len(names) == len(set(names)), profile


def test_stage_environment_drops_parent_test_instrumentation(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "parent")
    monkeypatch.setenv("COVERAGE_PROCESS_START", "coverage.ini")
    monkeypatch.setenv("COV_CORE_SOURCE", "src")
    env = verify_repository._build_stage_environment(tmp_path)
    assert "PYTEST_CURRENT_TEST" not in env
    assert "COVERAGE_PROCESS_START" not in env
    assert "COV_CORE_SOURCE" not in env
    assert env["PYTHONPATH"] == str(tmp_path / "src")


def test_release_profile_composes_static_and_release_tail() -> None:
    static = verify_repository.build_plan("static")
    tail = verify_repository.build_plan("release-tail")
    assert tail
    assert verify_repository.build_plan("release") == static + tail


def test_focused_regressions_use_only_required_pytest_plugin() -> None:
    stage = {item.name: item for item in verify_repository.build_plan("release-tail")}[
        "focused-regressions"
    ]
    assert stage.environment == (("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1"),)
    assert stage.command[stage.command.index("-p") + 1] == "pytest_asyncio.plugin"


def test_run_process_times_out_and_returns_control(tmp_path: Path) -> None:
    code, output, timed_out = verify_repository._run_process(
        [__import__("sys").executable, "-c", "import time; time.sleep(10)"],
        cwd=tmp_path,
        env=verify_repository._build_stage_environment(tmp_path),
        timeout_seconds=0.05,
    )
    assert code is None
    assert timed_out is True
    assert output == ""
