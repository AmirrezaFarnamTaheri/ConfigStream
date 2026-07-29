# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from scripts import resilient_stage


def test_normalize_status_maps_github_results() -> None:
    assert resilient_stage.normalize_status("success") == "success"
    assert resilient_stage.normalize_status("failure") == "failed"
    assert resilient_stage.normalize_status("cancelled") == "failed"
    assert resilient_stage.normalize_status("skipped") == "skipped"


def test_run_stage_redacts_child_output_and_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "super-secret-token-value"
    monkeypatch.setenv("TEST_API_KEY", secret)
    report_dir = tmp_path / "stages"
    result = resilient_stage.run_stage(
        "redaction",
        [sys.executable, "-c", f"print('token={secret}')"],
        report_dir,
        timeout=10,
    )
    assert result.status == "success"
    log = (report_dir / "redaction.log").read_text(encoding="utf-8")
    assert secret not in log
    assert "MASKED" in log or "REDACTED" in log
    assert all(secret not in argument for argument in result.command)


def test_run_stage_times_out(tmp_path: Path) -> None:
    result = resilient_stage.run_stage(
        "timeout",
        [sys.executable, "-c", "import time; time.sleep(2)"],
        tmp_path,
        timeout=0.1,
    )
    assert result.status == "failed"
    assert result.exit_code == 124
    assert result.failure_class == "timeout"


def test_run_stage_retries_and_succeeds(tmp_path: Path) -> None:
    marker = tmp_path / "attempt.txt"
    code = (
        "from pathlib import Path; import sys; "
        f"p=Path({str(marker)!r}); n=int(p.read_text())+1 if p.exists() else 1; "
        "p.write_text(str(n)); sys.exit(0 if n == 2 else 1)"
    )
    result = resilient_stage.run_stage(
        "retry",
        [sys.executable, "-c", code],
        tmp_path / "reports",
        timeout=10,
        retries=1,
        retry_backoff=0,
    )
    assert result.status == "success"
    assert len(result.attempts) == 2


def test_evaluate_readiness_is_fail_closed(tmp_path: Path) -> None:
    report_dir = tmp_path / "stages"
    resilient_stage.record_stage("good", "success", report_dir)
    required = tmp_path / "artifact.json"
    required.write_text("{}", encoding="utf-8")
    output = tmp_path / "readiness.json"
    result = resilient_stage.evaluate_readiness(
        report_dir, ["good", "missing"], [required], output
    )
    assert result["publish_ready"] is False
    assert "stage:missing:missing" in result["blockers"]
    assert json.loads(output.read_text(encoding="utf-8")) == result
