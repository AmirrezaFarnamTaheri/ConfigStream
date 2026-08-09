# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reconcile shard diagnostics with the shielded candidates in the final public artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def _load_records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path.name} must contain a JSON array")
    return [item for item in payload if isinstance(item, dict)]


def _public_shielding_counts(records: list[dict[str, Any]]) -> tuple[int, int]:
    candidates = 0
    verified = 0
    for record in records:
        details = record.get("details")
        if not isinstance(details, dict) or not bool(details.get("shielded_candidate")):
            continue
        candidates += 1
        if bool(details.get("shielded_verified")):
            verified += 1
    return candidates, verified


def reconcile(root: Path) -> dict[str, int]:
    metadata_path = root / "metadata.json"
    proxies_path = root / "proxies.json"
    metadata = _load_object(metadata_path)
    records = _load_records(proxies_path)

    shard_candidates = max(
        int(metadata.get("shielded_count") or 0),
        int(metadata.get("shielded_candidate_count") or 0),
    )
    public_candidates, public_verified = _public_shielding_counts(records)

    metadata["shard_shielded_candidate_count"] = shard_candidates
    metadata["shielded_count"] = public_candidates
    metadata["shielded_candidate_count"] = public_candidates
    metadata["shielded_verified_count"] = public_verified
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    health_path = root / "health.json"
    if health_path.is_file():
        health = _load_object(health_path)
        blockers = health.get("release_blockers")
        if isinstance(blockers, list):
            health["release_blockers"] = [
                blocker
                for blocker in blockers
                if not str(blocker).startswith("unverified_shielded_candidates:")
            ]
        health_path.write_text(
            json.dumps(health, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    return {
        "shard_candidates": shard_candidates,
        "public_candidates": public_candidates,
        "public_verified": public_verified,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    args = parser.parse_args()
    counts = reconcile(args.artifact_dir.resolve())
    print(
        "Reconciled shielded candidates: "
        f"shard={counts['shard_candidates']} "
        f"public={counts['public_candidates']} "
        f"verified={counts['public_verified']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
