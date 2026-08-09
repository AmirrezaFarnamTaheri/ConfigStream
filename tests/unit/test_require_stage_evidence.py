# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

from scripts import dynamic_reshard, require_stage_evidence, resilient_stage


def test_requirement_fails_when_stage_failed(tmp_path: Path) -> None:
    report_dir = tmp_path / "stages"
    resilient_stage.record_stage("normalize-source-timings", "failed", report_dir)
    normalized = tmp_path / "source_timing_normalized.log"
    evidence = tmp_path / "source_timing.jsonl"
    normalized.write_text("timing\n", encoding="utf-8")
    evidence.write_text("{}\n", encoding="utf-8")

    result = require_stage_evidence.main(
        [
            "--report-dir",
            str(report_dir),
            "--stage",
            "normalize-source-timings",
            "--required-file",
            str(normalized),
            "--required-file",
            str(evidence),
            "--output",
            str(tmp_path / "requirement.json"),
        ]
    )

    assert result == 1


def test_requirement_fails_when_evidence_is_empty(tmp_path: Path) -> None:
    report_dir = tmp_path / "stages"
    resilient_stage.record_stage("normalize-source-timings", "success", report_dir)
    normalized = tmp_path / "source_timing_normalized.log"
    evidence = tmp_path / "source_timing.jsonl"
    normalized.write_text("timing\n", encoding="utf-8")
    evidence.write_text("", encoding="utf-8")

    result = require_stage_evidence.main(
        [
            "--report-dir",
            str(report_dir),
            "--stage",
            "normalize-source-timings",
            "--required-file",
            str(normalized),
            "--required-file",
            str(evidence),
            "--output",
            str(tmp_path / "requirement.json"),
        ]
    )

    assert result == 1


def test_requirement_passes_only_with_successful_stage_and_evidence(
    tmp_path: Path,
) -> None:
    report_dir = tmp_path / "stages"
    resilient_stage.record_stage("normalize-source-timings", "success", report_dir)
    normalized = tmp_path / "source_timing_normalized.log"
    evidence = tmp_path / "source_timing.jsonl"
    normalized.write_text("timing\n", encoding="utf-8")
    evidence.write_text("{}\n", encoding="utf-8")
    output = tmp_path / "requirement.json"

    result = require_stage_evidence.main(
        [
            "--report-dir",
            str(report_dir),
            "--stage",
            "normalize-source-timings",
            "--required-file",
            str(normalized),
            "--required-file",
            str(evidence),
            "--output",
            str(output),
        ]
    )

    assert result == 0
    assert output.is_file()


def test_dynamic_reshard_stops_before_sources_when_prerequisites_fail(
    monkeypatch,
) -> None:
    monkeypatch.setattr(dynamic_reshard, "_timing_prerequisites_ready", lambda: False)

    assert dynamic_reshard.main() == 1
