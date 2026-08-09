# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reconcile final public proxy surfaces and release metadata."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from scripts.finalize_release_outputs import INTERNAL_KEYS, _clean_text, _source_host

PUBLIC_PROXY_ARRAYS = (
    "proxies.json",
    "proxies-dns-safe.json",
    "proxies-dns-hardened.json",
    "revived.json",
    "revived-dns-safe.json",
    "revived-dns-hardened.json",
)
PUBLIC_PROXY_DIRS = ("countries", "protocols")
PUBLIC_INTERNAL_DETAIL_KEYS = {
    *INTERNAL_KEYS,
    "shielded_candidate",
    "shielded_verified",
}


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


def _public_source(value: str) -> str | None:
    """Sanitize a source value without changing an already-public host/hash."""

    cleaned = _clean_text(value).strip()
    if not cleaned:
        return None
    if not any(marker in cleaned for marker in ("://", "/", "@", "?", "#")):
        return cleaned
    sanitized = _source_host(cleaned)
    return str(sanitized) if sanitized is not None else None


def _sanitize_public(
    value: Any,
    *,
    key: str | None = None,
    allow_error: bool = False,
) -> Any:
    """Apply the public proxy boundary idempotently.

    finalize_release_outputs already reduces canonical source URLs to a public
    host/hash. Reconciliation may run over those records again while also
    cleaning derivatives generated before finalization, so source sanitization
    must preserve an already-public scalar instead of hashing it a second time.

    The public proxy schema intentionally permits ``details.error`` for
    ``protocol: revived`` records. Other protocol-specific detail schemas are
    closed and must not receive tester error text. Shield-verification flags are
    release bookkeeping and are reduced to metadata counters before this pass.
    """

    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for raw_key, item in value.items():
            item_key = str(raw_key)
            lowered = item_key.lower()
            if item_key.startswith("_") or lowered in PUBLIC_INTERNAL_DETAIL_KEYS:
                continue
            if lowered == "error" and not allow_error:
                continue
            output[item_key] = _sanitize_public(item, key=item_key)
        return output
    if isinstance(value, list):
        return [_sanitize_public(item, key=key) for item in value]
    if isinstance(value, str):
        cleaned = _clean_text(value)
        if key == "source" or (key and "source" in key.lower()):
            return _public_source(cleaned)
        return cleaned
    return value


def _sanitize_proxy_record(record: dict[str, Any]) -> dict[str, Any]:
    protocol = str(record.get("protocol") or "").lower()
    output: dict[str, Any] = {}
    for raw_key, item in record.items():
        item_key = str(raw_key)
        if item_key == "details" and isinstance(item, dict):
            output[item_key] = _sanitize_public(
                item,
                key=item_key,
                allow_error=protocol == "revived",
            )
        else:
            output[item_key] = _sanitize_public(item, key=item_key)
    return output


def _sanitize_proxy_array(path: Path) -> bool:
    if not path.is_file():
        return False
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return False
    sanitized = [
        _sanitize_proxy_record(item) if isinstance(item, dict) else _sanitize_public(item)
        for item in payload
    ]
    if sanitized == payload:
        return False
    path.write_text(
        json.dumps(sanitized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return True


def _sanitize_public_proxy_surfaces(root: Path) -> list[str]:
    changed: list[str] = []
    for relative in PUBLIC_PROXY_ARRAYS:
        path = root / relative
        if _sanitize_proxy_array(path):
            changed.append(relative)
    for directory_name in PUBLIC_PROXY_DIRS:
        directory = root / directory_name
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.list*.json")):
            if _sanitize_proxy_array(path):
                changed.append(path.relative_to(root).as_posix())
    return changed


def _sync_api_alias(root: Path, canonical: str, alias: str) -> None:
    source = root / canonical
    destination = root / alias
    if not source.is_file():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


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


def _write_evidence(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def reconcile(root: Path, evidence_path: Path | None = None) -> dict[str, Any]:
    metadata_path = root / "metadata.json"
    proxies_path = root / "proxies.json"
    metadata = _load_object(metadata_path)
    raw_records = _load_records(proxies_path)

    shard_candidates = max(
        int(metadata.get("shielded_count") or 0),
        int(metadata.get("shielded_candidate_count") or 0),
    )
    public_candidates, public_verified = _public_shielding_counts(raw_records)

    changed_surfaces = _sanitize_public_proxy_surfaces(root)

    metadata["shielded_count"] = public_candidates
    metadata["shielded_candidate_count"] = public_candidates
    metadata["shielded_verified_count"] = public_verified
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    _sync_api_alias(root, "proxies.json", "api/proxies")
    _sync_api_alias(root, "metadata.json", "api/stats")

    health_path = root / "health.json"
    if health_path.is_file():
        health = _load_object(health_path)
        blockers = health.get("release_blockers")
        if isinstance(blockers, list):
            reconciled_blockers = [
                blocker
                for blocker in blockers
                if not str(blocker).startswith("unverified_shielded_candidates:")
            ]
            if public_candidates > public_verified:
                reconciled_blockers.append(
                    "unverified_shielded_candidates:"
                    f"{public_candidates - public_verified}"
                )
            health["release_blockers"] = reconciled_blockers
        health_path.write_text(
            json.dumps(health, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    result: dict[str, Any] = {
        "schema_version": 1,
        "shard_candidates": shard_candidates,
        "public_candidates": public_candidates,
        "public_verified": public_verified,
        "sanitized_surfaces": changed_surfaces,
    }
    if evidence_path is not None:
        _write_evidence(evidence_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument(
        "--evidence",
        type=Path,
        help="Optional private evidence file for pre-publication shard diagnostics.",
    )
    args = parser.parse_args()
    result = reconcile(args.artifact_dir.resolve(), args.evidence)
    print(
        "Reconciled public artifact: "
        f"shard_candidates={result['shard_candidates']} "
        f"public_candidates={result['public_candidates']} "
        f"verified={result['public_verified']} "
        f"sanitized_surfaces={len(result['sanitized_surfaces'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
