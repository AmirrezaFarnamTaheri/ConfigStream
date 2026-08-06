# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression coverage for final PR531 review findings."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType


def _load_script(name: str) -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_nested_artifact_manifest_is_public_content(tmp_path: Path) -> None:
    release_gate = _load_script("release_gate")
    (tmp_path / "artifact_manifest.json").write_text("{}", encoding="utf-8")
    nested = tmp_path / "nested" / "artifact_manifest.json"
    nested.parent.mkdir()
    nested.write_text("{}", encoding="utf-8")

    entries = release_gate.manifest_entries(tmp_path)

    assert [item["path"] for item in entries] == ["nested/artifact_manifest.json"]


def test_missing_required_native_target_fails_closed(
    tmp_path: Path, monkeypatch
) -> None:
    native_checks = _load_script("native_client_checks")
    report = tmp_path / "report.json"
    fake_binary = tmp_path / "validator"
    fake_binary.write_bytes(b"binary")
    monkeypatch.setattr(native_checks.shutil, "which", lambda _name: str(fake_binary))
    monkeypatch.setattr(
        "sys.argv",
        ["native_client_checks.py", str(tmp_path), "--report", str(report)],
    )

    assert native_checks.main() == 1
    payload = native_checks.json.loads(report.read_text(encoding="utf-8"))
    missing = {
        (item["core"], item["path"])
        for item in payload["checks"]
        if item["error"] == "required native artifact is unavailable"
    }
    assert missing == {
        ("sing-box", "singbox.json"),
        ("mihomo", "clash.yaml"),
        ("xray", "xray.json"),
    }


def test_native_validator_error_is_sanitized(tmp_path: Path, monkeypatch) -> None:
    native_checks = _load_script("native_client_checks")
    artifact = tmp_path / "xray.json"
    artifact.write_text("{}", encoding="utf-8")
    binary = tmp_path / "xray"
    binary.write_bytes(b"binary")
    secret = "https://user:super-secret@example.com?token=abc123"
    monkeypatch.setattr(
        native_checks.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, stdout="", stderr=secret
        ),
    )

    result = native_checks.run(
        tmp_path, [str(binary), "check", str(artifact)], "xray", artifact, "digest"
    )

    assert result["status"] == "failed"
    assert "super-secret" not in result["error"]
    assert "abc123" not in result["error"]
    assert "[MASKED]" in result["error"]
