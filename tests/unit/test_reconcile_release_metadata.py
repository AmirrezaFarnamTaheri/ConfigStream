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
    record = {
        "id": "candidate",
        "protocol": "vless",
        "details": {
            "tester_error_category": "IPC_ERROR",
            "failure_category": "TIMEOUT",
            "safe_public_field": "keep",
        },
    }
    _write(root / "proxies.json", [record])
    _write(root / "api" / "proxies", [record])
    _write(root / "revived-dns-safe.json", [record])
    _write(root / "countries" / "XX.list-dns-hardened.json", [record])
    _write(
        root / "metadata.json",
        {
            "shielded_count": 4,
            "shielded_candidate_count": 0,
            "shielded_verified_count": 0,
        },
    )
    _write(root / "api" / "stats", {"stale": True})

    result = reconcile(root)

    assert result["shard_candidates"] == 4
    assert sorted(result["sanitized_surfaces"]) == [
        "countries/XX.list-dns-hardened.json",
        "proxies.json",
        "revived-dns-safe.json",
    ]
    for path in (
        root / "proxies.json",
        root / "revived-dns-safe.json",
        root / "countries" / "XX.list-dns-hardened.json",
    ):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload[0]["details"] == {"safe_public_field": "keep"}

    assert (root / "api" / "proxies").read_bytes() == (root / "proxies.json").read_bytes()
    assert (root / "api" / "stats").read_bytes() == (root / "metadata.json").read_bytes()
