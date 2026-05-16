# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for core compatibility report validation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import validate_core_compatibility


def _write_json(path: Path, data: dict[str, object]) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _valid_report() -> dict[str, object]:
    return {
        "core_formats": [
            {
                "core": "sing-box",
                "status": "stable",
                "pipeline_outputs": ["singbox.json"],
            },
            {
                "core": "xray",
                "status": "planned",
                "pipeline_outputs": [],
            },
        ],
        "forbidden_pipeline_outputs_until_generated": ["xray.json"],
    }


def _output_matrix(paths: list[str]) -> dict[str, object]:
    outputs = []
    for path in paths:
        item: dict[str, object] = {"path": path}
        if path.startswith("singbox"):
            item.update({"core_format": "sing-box", "artifact_type": "full_config"})
        elif path.startswith("chains"):
            item.update(
                {"core_format": "sing-box", "artifact_type": "full_config_alias"}
            )
        elif path.startswith("clash"):
            item.update({"core_format": "clash", "artifact_type": "full_config"})
        outputs.append(item)
    return {"outputs": outputs}


def test_validate_core_compatibility_accepts_current_repo() -> None:
    assert validate_core_compatibility.validate_core_compatibility() == []


def test_validate_core_compatibility_accepts_valid_report(
    tmp_path: Path, monkeypatch
) -> None:
    report = _write_json(tmp_path / "core_compatibility_report.json", _valid_report())
    matrix = _write_json(
        tmp_path / "output_matrix.json", _output_matrix(["singbox.json"])
    )
    monkeypatch.setattr(validate_core_compatibility, "OUTPUT_MATRIX_PATH", matrix)

    assert validate_core_compatibility.validate_core_compatibility(report) == []


def test_validate_core_compatibility_rejects_missing_output(
    tmp_path: Path, monkeypatch
) -> None:
    report = _write_json(tmp_path / "core_compatibility_report.json", _valid_report())
    matrix = _write_json(tmp_path / "output_matrix.json", _output_matrix([]))
    monkeypatch.setattr(validate_core_compatibility, "OUTPUT_MATRIX_PATH", matrix)

    errors = validate_core_compatibility.validate_core_compatibility(report)

    assert any("references missing output: singbox.json" in error for error in errors)


def test_validate_core_compatibility_rejects_forbidden_xray_output(
    tmp_path: Path, monkeypatch
) -> None:
    report = _write_json(tmp_path / "core_compatibility_report.json", _valid_report())
    matrix = _write_json(
        tmp_path / "output_matrix.json", _output_matrix(["singbox.json", "xray.json"])
    )
    monkeypatch.setattr(validate_core_compatibility, "OUTPUT_MATRIX_PATH", matrix)

    errors = validate_core_compatibility.validate_core_compatibility(report)

    assert any("xray.json" in error for error in errors)


def test_validate_core_compatibility_rejects_core_format_drift(
    tmp_path: Path, monkeypatch
) -> None:
    report = _write_json(tmp_path / "core_compatibility_report.json", _valid_report())
    matrix = _write_json(
        tmp_path / "output_matrix.json",
        {
            "outputs": [
                {
                    "path": "singbox.json",
                    "core_format": "clash",
                    "artifact_type": "full_config",
                }
            ]
        },
    )
    monkeypatch.setattr(validate_core_compatibility, "OUTPUT_MATRIX_PATH", matrix)

    errors = validate_core_compatibility.validate_core_compatibility(report)

    assert any("mismatched core_format" in error for error in errors)


def test_validate_core_compatibility_requires_xray_status(tmp_path: Path) -> None:
    data = _valid_report()
    data["core_formats"] = [data["core_formats"][0]]  # type: ignore[index]
    report = _write_json(tmp_path / "core_compatibility_report.json", data)

    errors = validate_core_compatibility.validate_core_compatibility(report)

    assert any("Xray status" in error for error in errors)
