# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "main.yml"


def _artifact_record_step() -> str:
    workflow = MAIN_WORKFLOW.read_text(encoding="utf-8")
    return workflow.split("      - name: Record artifact downloads", 1)[1].split(
        "      - name: Restore available artifacts", 1
    )[0]


def test_main_records_shard_download_only_after_exact_lineage_validation() -> None:
    record_step = _artifact_record_step()

    assert 'shard_status="${{ steps.shard_download.outcome }}"' in record_step
    assert (
        'matrix_status="${{ steps.matrix_artifact_download.outcome }}"' in record_step
    )
    assert '[ "$matrix_status" != success ]' in record_step
    assert "matrix-artifact/source-matrix.json" in record_step
    assert 'Path("artifacts").rglob("shard_lineage.json")' in record_step
    for identity_field in ("batch", "part", "source_file", "source_sha256"):
        assert f'row.get("{identity_field}")' in record_step
        assert f'payload.get("{identity_field}")' in record_step
    assert "Counter(observed)" in record_step
    assert "missing = sorted(expected - observed_set)" in record_step
    assert "unexpected = sorted(observed_set - expected)" in record_step
    assert "duplicates = sorted" in record_step
    assert "shard artifact lineage mismatch" in record_step

    record = 'record --name shard-download --status "$shard_status"'
    assert record in record_step
    assert record_step.index("shard artifact lineage mismatch") < record_step.index(
        record
    )


def test_main_records_matrix_failure_even_when_matrix_file_is_missing() -> None:
    record_step = _artifact_record_step()

    assert (
        "Shard artifact validation requires the exact runtime source matrix"
        in record_step
    )
    assert "shard_status=failure" in record_step
    matrix_record = 'record --name matrix-artifact-download --status "$matrix_status"'
    assert matrix_record in record_step
    assert record_step.index("shard_status=failure") < record_step.index(matrix_record)


def test_geoip_prerequisite_is_geoip_only_and_retained_for_reruns() -> None:
    workflow = MAIN_WORKFLOW.read_text(encoding="utf-8")

    assert "python -m configstream.cli update-databases --geoip-only" in workflow
    geoip_section = workflow.split("  setup_geoip:", 1)[1].split("  setup_matrix:", 1)[
        0
    ]
    assert "retention-days: 30" in geoip_section
