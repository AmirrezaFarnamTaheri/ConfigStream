# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.dynamic_reshard import _require_normalized_timing_inputs


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_dynamic_reshard_rejects_failed_timing_stage(tmp_path: Path) -> None:
    stage = tmp_path / "pipeline-evidence" / "stages" / "normalize-source-timings.json"
    normalized = tmp_path / "source_timing_normalized.log"
    evidence = tmp_path / "pipeline-evidence" / "source_timing.jsonl"
    _write_json(stage, {"name": "normalize-source-timings", "status": "failed"})
    normalized.write_text(
        "Source Summary [https://a.example/sub]: Raw=1 Dur=1000ms\n",
        encoding="utf-8",
    )
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(
        '{"source_url":"https://a.example/sub","duration_ms":1000}\n',
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="did not succeed"):
        _require_normalized_timing_inputs(stage, normalized, evidence)


def test_dynamic_reshard_requires_nonempty_normalized_artifacts(tmp_path: Path) -> None:
    stage = tmp_path / "pipeline-evidence" / "stages" / "normalize-source-timings.json"
    normalized = tmp_path / "source_timing_normalized.log"
    evidence = tmp_path / "pipeline-evidence" / "source_timing.jsonl"
    _write_json(stage, {"name": "normalize-source-timings", "status": "success"})
    normalized.write_text("", encoding="utf-8")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("", encoding="utf-8")

    with pytest.raises(RuntimeError, match="missing or empty"):
        _require_normalized_timing_inputs(stage, normalized, evidence)


def test_dynamic_reshard_accepts_successful_normalized_evidence(tmp_path: Path) -> None:
    stage = tmp_path / "pipeline-evidence" / "stages" / "normalize-source-timings.json"
    normalized = tmp_path / "source_timing_normalized.log"
    evidence = tmp_path / "pipeline-evidence" / "source_timing.jsonl"
    _write_json(stage, {"name": "normalize-source-timings", "status": "success"})
    normalized.write_text(
        "Source Summary [https://a.example/sub]: Raw=1 Dur=1000ms\n",
        encoding="utf-8",
    )
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(
        '{"source_url":"https://a.example/sub","duration_ms":1000}\n',
        encoding="utf-8",
    )

    _require_normalized_timing_inputs(stage, normalized, evidence)
