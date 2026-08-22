# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts import verify_repository


def test_posix_executable_check_requires_execute_permission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "validator"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    monkeypatch.setattr(verify_repository.os, "access", lambda _path, _mode: False)

    assert (
        verify_repository._is_executable_file(executable, platform_name="posix")
        is False
    )


@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (PermissionError("execution denied"), 126),
        (OSError("process creation failed"), 127),
    ],
)
def test_process_start_os_error_becomes_failed_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: OSError,
    expected_code: int,
) -> None:
    monkeypatch.setattr(
        verify_repository.subprocess,
        "Popen",
        Mock(side_effect=error),
    )

    code, output, timed_out = verify_repository._run_process(
        ["blocked-validator"],
        cwd=tmp_path,
        env=verify_repository._build_stage_environment(tmp_path),
        timeout_seconds=1,
    )

    assert code == expected_code
    assert output == f"could not start process: {error}"
    assert timed_out is False


def test_windows_timeout_terminates_descendant_tree_with_argument_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = Mock(spec=subprocess.Popen)
    process.pid = 4321
    process.kill = Mock()
    completed: subprocess.CompletedProcess[bytes] = subprocess.CompletedProcess([], 0)
    run = Mock(return_value=completed)

    monkeypatch.setattr(
        verify_repository.shutil,
        "which",
        lambda command: rf"C:\Windows\System32\{command}.exe",
    )
    monkeypatch.setattr(verify_repository.subprocess, "run", run)

    verify_repository._terminate_process_tree(process, platform_name="nt")

    run.assert_called_once_with(
        [r"C:\Windows\System32\taskkill.exe", "/PID", "4321", "/T", "/F"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    process.kill.assert_not_called()


def test_windows_tree_termination_falls_back_when_taskkill_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = Mock(spec=subprocess.Popen)
    process.pid = 4321
    process.kill = Mock()

    monkeypatch.setattr(verify_repository.shutil, "which", lambda _command: None)

    verify_repository._terminate_process_tree(process, platform_name="nt")

    process.kill.assert_called_once_with()
