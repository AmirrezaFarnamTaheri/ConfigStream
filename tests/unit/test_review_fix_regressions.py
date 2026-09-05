# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from scripts import dynamic_reshard
from scripts import validate_frontend_placeholders as frontend_validator
from scripts import validate_workflows
from scripts.normalize_source_timing_logs import SourceTiming, write_outputs

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_workflow(name: str) -> dict[object, object]:
    data = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
    )
    assert isinstance(data, dict)
    return data


def _step_by_name(job: object, name: str) -> dict[str, object]:
    assert isinstance(job, dict)
    steps = job.get("steps", [])
    assert isinstance(steps, list)
    for step in steps:
        if isinstance(step, dict) and step.get("name") == name:
            return step
    raise AssertionError(f"step not found: {name}")


def test_timing_outputs_sanitize_source_credentials(tmp_path: Path) -> None:
    raw_url = "https://user:super-secret@example.com/sub?token=abc123"
    records = [
        SourceTiming(
            url=raw_url,
            raw=10,
            duration_ms=2500.0,
            fetch_ms=250.0,
            source_log="pipeline_batch.log?token=log-secret",
        )
    ]
    normalized = tmp_path / "source_timing_normalized.log"
    evidence = tmp_path / "source_timing.jsonl"

    write_outputs(records, normalized, evidence)

    normalized_text = normalized.read_text(encoding="utf-8")
    evidence_text = evidence.read_text(encoding="utf-8")
    for secret in ("super-secret", "abc123", "log-secret"):
        assert secret not in normalized_text
        assert secret not in evidence_text
    assert "[MASKED]" in normalized_text
    payload = json.loads(evidence_text)
    assert payload["source_id"] == hashlib.sha256(raw_url.encode("utf-8")).hexdigest()


def test_structured_timing_evidence_maps_opaque_id_to_configured_url(
    tmp_path: Path,
) -> None:
    raw_url = "https://user:super-secret@example.com/sub?token=abc123"
    evidence = tmp_path / "source_timing.jsonl"
    evidence.write_text(
        json.dumps(
            {
                "source_id": hashlib.sha256(raw_url.encode("utf-8")).hexdigest(),
                "source_url": ("https://user:[MASKED]@example.com/sub?token=[MASKED]"),
                "raw": 10,
                "duration_ms": 2500.0,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert dynamic_reshard.parse_timing_evidence(evidence, {raw_url}) == {
        raw_url: (10, 2.5)
    }


def test_frontend_validation_sanitizes_invalid_key_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_injection(*_args: object, **_kwargs: object) -> list[str]:
        raise ValueError("token=frontend-super-secret")

    monkeypatch.setattr(frontend_validator, "inject_frontend_keys", fail_injection)

    assert frontend_validator.main([str(tmp_path), "--inject-env"]) == 1
    error = capsys.readouterr().err
    assert "frontend-super-secret" not in error
    assert "token=[MASKED]" in error


def test_release_gate_scopes_signing_key_to_release_process() -> None:
    data = _load_workflow("main.yml")
    jobs = data.get("jobs")
    assert isinstance(jobs, dict)
    step = _step_by_name(
        jobs["merge_validate_publish"], "Run every mandatory release gate"
    )
    command = step.get("run")
    assert isinstance(command, str)
    step_env = step.get("env", {})
    assert isinstance(step_env, dict)
    assert "CS_SIGNING_PRIVATE_KEY_HEX" not in step_env
    release_line = next(
        line for line in command.splitlines() if "release_gate.py" in line
    )
    assert "CS_SIGNING_PRIVATE_KEY_HEX=" in release_line
    for marker in (
        "native_client_checks.py",
        "validate_pages_artifact.py",
        "generate_evidence_bundle.py",
    ):
        marker_line = next(line for line in command.splitlines() if marker in line)
        assert "CS_SIGNING_PRIVATE_KEY_HEX" not in marker_line


def test_native_report_contract_rejects_writer_flag_with_any_path() -> None:
    data = deepcopy(_load_workflow("main.yml"))
    jobs = data.get("jobs")
    assert isinstance(jobs, dict)
    step = _step_by_name(
        jobs["merge_validate_publish"], "Run every mandatory release gate"
    )
    command = step.get("run")
    assert isinstance(command, str)
    step["run"] = command + (
        "\npython scripts/validate_pages_artifact.py --native-report-file "
        "pipeline-evidence/other-native-report.json output\n"
    )
    assert validate_workflows._main_native_output_contract(data) is False


def test_structured_timing_rejects_non_finite_duration(tmp_path: Path) -> None:
    raw_url = "https://example.com/source"
    evidence = tmp_path / "source_timing.jsonl"
    evidence.write_text(
        json.dumps(
            {
                "source_id": hashlib.sha256(raw_url.encode("utf-8")).hexdigest(),
                "raw": 10,
                "duration_ms": "Infinity",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert dynamic_reshard.parse_timing_evidence(evidence, {raw_url}) == {}


def test_structured_timing_skips_malformed_records(tmp_path: Path) -> None:
    raw_url = "https://example.com/source"
    source_id = hashlib.sha256(raw_url.encode()).hexdigest()
    evidence = tmp_path / "timing.jsonl"
    rows: list[object] = [
        [],
        None,
        {"source_id": source_id, "raw": float("inf"), "duration_ms": 100},
        {"source_id": source_id, "raw": -1, "duration_ms": 100},
        {"source_id": source_id, "raw": 2, "duration_ms": 1000},
    ]
    evidence.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    assert dynamic_reshard.parse_timing_evidence(evidence, {raw_url}) == {
        raw_url: (2, 1.0)
    }
