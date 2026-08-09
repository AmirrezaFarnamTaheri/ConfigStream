# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from scripts.reconcile_release_metadata import reconcile


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
    derivative_record = {
        **finalized_record,
        "source": "https://user:secret@example.com/sub?token=secret",
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
    _write(root / "proxies.json", [finalized_record])
    _write(root / "api" / "proxies", [finalized_record])
    _write(root / "revived-dns-safe.json", [derivative_record, revived_record])
    _write(root / "countries" / "XX.list-dns-hardened.json", [derivative_record])
    _write(
        root / "metadata.json",
        {
            "shielded_count": 4,
            "shielded_candidate_count": 0,
            "shielded_verified_count": 0,
        },
    )
    _write(root / "api" / "stats", {"stale": True})

    result = reconcile(root, evidence_path)

    assert result["shard_candidates"] == 4
    assert sorted(result["sanitized_surfaces"]) == [
        "countries/XX.list-dns-hardened.json",
        "proxies.json",
        "revived-dns-safe.json",
    ]
    for path in (
        root / "proxies.json",
        root / "countries" / "XX.list-dns-hardened.json",
    ):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload[0]["source"] == "example.com"
        assert payload[0]["details"] == {"safe_public_field": "keep"}

    revived_payload = json.loads(
        (root / "revived-dns-safe.json").read_text(encoding="utf-8")
    )
    assert revived_payload[0]["source"] == "example.com"
    assert revived_payload[0]["details"] == {"safe_public_field": "keep"}
    assert revived_payload[1]["source"] == "revived.example"
    assert revived_payload[1]["details"] == {
        "is_revived": True,
        "error": "original transport failed",
    }

    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    assert "shard_shielded_candidate_count" not in metadata
    assert metadata["shielded_count"] == 0
    assert metadata["shielded_candidate_count"] == 0
    assert metadata["shielded_verified_count"] == 0
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["schema_version"] == 1
    assert evidence["shard_candidates"] == 4
    assert evidence["public_candidates"] == 0
    assert evidence["public_verified"] == 0

    assert (root / "api" / "proxies").read_bytes() == (
        root / "proxies.json"
    ).read_bytes()
    assert (root / "api" / "stats").read_bytes() == (
        root / "metadata.json"
    ).read_bytes()
