# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import generate_triage_report


def _write_json(path: Path, payload: object) -> None:
    """Write one JSON fixture, creating its parent directories first."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_triage_report_check_accepts_crlf_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Treat CRLF and LF report content as semantically equivalent."""

    _write_json(
        tmp_path / "docs" / "readiness.json",
        {
            "project_version": "3.2.0",
            "verdict": "blocked",
            "production_ready": False,
        },
    )
    _write_json(tmp_path / "docs" / "debt_matrix.json", {"summary": {"total": 280}})
    _write_json(
        tmp_path / "src" / "configstream" / "data" / "source-admission.json",
        {"entry_count": 1025, "source_set_sha256": "abc123"},
    )
    _write_json(
        tmp_path / "config" / "exception-boundary-budget.json",
        {"total_ceiling": 254},
    )
    _write_json(
        tmp_path / "config" / "function-size-budget.json",
        {"functions": {"oversized": 301}},
    )

    monkeypatch.setattr(generate_triage_report, "ROOT", tmp_path)
    monkeypatch.setattr(generate_triage_report, "OUTPUT", tmp_path / "TRIAGE_REPORT.md")

    expected = generate_triage_report.render()
    generate_triage_report.OUTPUT.write_bytes(
        expected.replace("\n", "\r\n").encode("utf-8")
    )

    assert generate_triage_report.is_current(expected) is True
