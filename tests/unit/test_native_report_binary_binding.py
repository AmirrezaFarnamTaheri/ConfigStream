# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts.release_gate import REQUIRED_NATIVE_TARGETS, digest, validate_native_report


def _valid_report(root: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    tool_digests = {
        "sing-box": "1" * 64,
        "mihomo": "2" * 64,
        "xray": "3" * 64,
    }
    checks: list[dict[str, Any]] = []
    for core, relative in REQUIRED_NATIVE_TARGETS.items():
        artifact = root / relative
        artifact.write_text(f"{core}\n", encoding="utf-8")
        checks.append(
            {
                "core": core,
                "path": relative,
                "status": "passed",
                "artifact_sha256": digest(artifact),
                "binary_sha256": tool_digests[core],
            }
        )

    proxies = root / "proxies.json"
    proxies.write_text("[]\n", encoding="utf-8")
    checks.append(
        {
            "core": "sing-box-connectivity:vless",
            "path": "proxies.json",
            "status": "passed",
            "artifact_sha256": digest(proxies),
            "binary_sha256": tool_digests["sing-box"],
        }
    )
    report: dict[str, Any] = {
        "schema_version": 2,
        "tools": {
            name: {"available": True, "binary_sha256": value}
            for name, value in tool_digests.items()
        },
        "checks": checks,
        "summary": {"passed": len(checks), "failed": 0, "skipped": 0},
    }
    for report_key, env_key, value in (
        ("source_commit", "GITHUB_SHA", "test-source-commit"),
        ("run_id", "GITHUB_RUN_ID", "test-run-id"),
        ("run_attempt", "GITHUB_RUN_ATTEMPT", "test-run-attempt"),
    ):
        monkeypatch.setenv(env_key, value)
        report[report_key] = value
    return report


def test_native_report_accepts_checks_bound_to_reported_validator_digests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _valid_report(tmp_path, monkeypatch)

    assert validate_native_report(tmp_path, report) == []


def test_native_report_rejects_connectivity_check_with_mismatched_binary_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _valid_report(tmp_path, monkeypatch)
    connectivity = next(
        check
        for check in report["checks"]
        if check["core"] == "sing-box-connectivity:vless"
    )
    connectivity["binary_sha256"] = "f" * 64

    errors = validate_native_report(tmp_path, report)

    assert (
        "native validation binary digest mismatch: "
        "sing-box-connectivity:vless:proxies.json"
    ) in errors
