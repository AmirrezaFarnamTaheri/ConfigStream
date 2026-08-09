# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.reconcile_release_metadata import reconcile

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "reconcile_release_metadata.py"


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_reconcile_sanitizes_root_and_categorized_proxy_arrays(tmp_path: Path) -> None:
    root = tmp_path / "output"
    root.mkdir()
    evidence_path = tmp_path / "pipeline-evidence" / "shielded_reconciliation.json"
    finalized_record = {
        "id": "candidate",
        "protocol": "vless",
        "source": "example.com",
        "details": {
            "tester_error_category": "IPC_ERROR",
            "failure_category": "TIMEOUT",
            "error": "bounded tester failed",
            "safe_public_field": "keep",
        },
    }
    shielded_record = {
        "id": "shielded",
        "protocol": "chain",
        "source": "shield.example",
        "details": {
            "shielded_candidate": True,
            "shielded_verified": True,
            "processed_by": ["shielding"],
        },
    }
    derivative_record = {
        **finalized_record,
        "source": "https://user:secret@example.com/sub?token=secret",
        "_source": "https://internal.example/private",
        "source_url": "https://internal.example/raw",
    }
    revived_record = {
        "id": "revived",
        "protocol": "revived",
        "source": "https://revived.example/sub?token=secret",
        "details": {
            "is_revived": True,
            "error": "original transport failed",
            "tester_error_category": "IPC_ERROR",
        },
    }
    _write(root / "proxies.json", [finalized_record, shielded_record])
    _write(root / "api" / "proxies", [finalized_record, shielded_record])
    _write(root / "revived-dns-safe.json", [derivative_record, revived_record])
    _write(root / "countries" / "XX.list-dns-hardened.json", [derivative_record])
    _write(
        root / "metadata.json",
        {
            "shielded_count": 4,
            "shielded_candidate_count": 4,
            "shielded_verified_count": 2,
        },
    )
    _write(root / "api" / "stats", {"stale": True})

    result = reconcile(root, evidence_path)

    assert result["shard_candidates"] == 4
    assert result["public_candidates"] == 1
    assert result["public_verified"] == 1
    assert sorted(result["sanitized_surfaces"]) == [
        "countries/XX.list-dns-hardened.json",
        "proxies.json",
        "revived-dns-safe.json",
    ]
    proxies = json.loads((root / "proxies.json").read_text(encoding="utf-8"))
    assert proxies[0]["source"] == "example.com"
    assert proxies[0]["details"] == {"safe_public_field": "keep"}
    assert proxies[1]["details"] == {
        "shielded_candidate": True,
        "shielded_verified": True,
        "processed_by": ["shielding"],
    }

    country_payload = json.loads(
        (root / "countries" / "XX.list-dns-hardened.json").read_text(encoding="utf-8")
    )
    assert country_payload[0]["source"] == "example.com"
    assert "_source" not in country_payload[0]
    assert "source_url" not in country_payload[0]
    assert country_payload[0]["details"] == {"safe_public_field": "keep"}

    revived_payload = json.loads(
        (root / "revived-dns-safe.json").read_text(encoding="utf-8")
    )
    assert revived_payload[0]["source"] == "example.com"
    assert "_source" not in revived_payload[0]
    assert "source_url" not in revived_payload[0]
    assert revived_payload[0]["details"] == {"safe_public_field": "keep"}
    assert revived_payload[1]["source"] == "revived.example"
    assert revived_payload[1]["details"] == {
        "is_revived": True,
        "error": "original transport failed",
    }

    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    assert "shard_shielded_candidate_count" not in metadata
    assert metadata["shielded_count"] == 1
    assert metadata["shielded_candidate_count"] == 1
    assert metadata["shielded_verified_count"] == 1
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["schema_version"] == 1
    assert evidence["shard_candidates"] == 4
    assert evidence["public_candidates"] == 1
    assert evidence["public_verified"] == 1

    assert (root / "api" / "proxies").read_bytes() == (
        root / "proxies.json"
    ).read_bytes()
    assert (root / "api" / "stats").read_bytes() == (
        root / "metadata.json"
    ).read_bytes()


def test_reconcile_keeps_unverified_public_shielded_candidate_blocking(
    tmp_path: Path,
) -> None:
    root = tmp_path / "output"
    root.mkdir()
    _write(
        root / "proxies.json",
        [
            {
                "id": "shielded",
                "protocol": "chain",
                "details": {
                    "shielded_candidate": True,
                    "shielded_verified": False,
                    "processed_by": ["shielding"],
                },
            }
        ],
    )
    _write(
        root / "metadata.json",
        {
            "shielded_count": 9,
            "shielded_candidate_count": 9,
            "shielded_verified_count": 8,
        },
    )
    _write(
        root / "health.json",
        {"release_blockers": ["unverified_shielded_candidates:9"]},
    )

    result = reconcile(root)

    assert result["shard_candidates"] == 9
    assert result["public_candidates"] == 1
    assert result["public_verified"] == 0
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["shielded_candidate_count"] == 1
    assert metadata["shielded_verified_count"] == 0
    health = json.loads((root / "health.json").read_text(encoding="utf-8"))
    assert health["release_blockers"] == ["unverified_shielded_candidates:1"]
    public = json.loads((root / "proxies.json").read_text(encoding="utf-8"))
    assert public[0]["details"] == {
        "shielded_candidate": True,
        "shielded_verified": False,
        "processed_by": ["shielding"],
    }


def test_reconcile_runs_as_direct_workflow_script(tmp_path: Path) -> None:
    root = tmp_path / "output"
    root.mkdir()
    _write(root / "proxies.json", [])
    _write(
        root / "metadata.json",
        {
            "shielded_count": 0,
            "shielded_candidate_count": 0,
            "shielded_verified_count": 0,
        },
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(root)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Reconciled public artifact" in result.stdout
    evidence_path = tmp_path / "pipeline-evidence" / "shielded_reconciliation.json"
    assert evidence_path.is_file()
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence == {
        "public_candidates": 0,
        "public_verified": 0,
        "sanitized_surfaces": [],
        "schema_version": 1,
        "shard_candidates": 0,
    }
