#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sanitize, normalize, validate, and seal one immutable public release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from configstream.publication import (
    PUBLIC_PRIVATE_BASENAMES as PRIVATE_NAMES,
    PUBLIC_PRIVATE_SUFFIXES as PRIVATE_SUFFIXES,
    validate_public_artifact,
    write_release_manifest,
)


def _purge_private_state(root: Path) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file() and (
            path.name in PRIVATE_NAMES or path.suffix.lower() in PRIVATE_SUFFIXES
        ):
            path.unlink()
        elif path.is_dir() and path.name.lower() in {
            "private",
            "private-state",
            "cache",
            "fingerprints",
        }:
            shutil.rmtree(path)
    for directory in sorted(root.rglob("*"), reverse=True):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid required JSON file {path}: {exc}") from exc


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _is_verified_stable_record(record: object) -> bool:
    if not isinstance(record, dict) or record.get("is_working") is not True:
        return False
    details = record.get("details")
    details = details if isinstance(details, dict) else {}
    tags = record.get("tags")
    tags = {str(item).lower() for item in tags} if isinstance(tags, list) else set()
    is_candidate = bool(details.get("shielded_candidate")) or "candidate" in tags
    is_verified = bool(details.get("shielded_verified")) or "verified" in tags
    return not is_candidate or is_verified


def _sort_port(item: dict[str, Any]) -> int:
    try:
        return int(item.get("port") or 0)
    except (TypeError, ValueError) as exc:
        raise SystemExit(
            "release rejected: proxy record has a non-numeric port"
        ) from exc


def _partition_and_normalize_public_records(
    root: Path,
) -> tuple[list[dict], list[dict]]:
    source = _load_json(root / "proxies.json")
    if not isinstance(source, list):
        raise SystemExit("release rejected: proxies.json must be a JSON list")

    stable: list[dict] = []
    experimental: list[dict] = []
    seen: set[str] = set()
    for item in source:
        if not isinstance(item, dict):
            continue
        config = item.get("config")
        identity_material = str(
            config or item.get("id") or json.dumps(item, sort_keys=True)
        )
        identity = hashlib.sha256(identity_material.encode("utf-8")).hexdigest()
        if identity in seen:
            continue
        seen.add(identity)
        if _is_verified_stable_record(item):
            stable.append(item)
        else:
            experimental.append(item)

    if not stable:
        raise SystemExit(
            "release rejected: no verified working records for stable channel"
        )

    stable.sort(
        key=lambda item: (
            str(item.get("protocol") or ""),
            str(item.get("country_code") or ""),
            str(item.get("address") or ""),
            _sort_port(item),
            str(item.get("id") or ""),
        )
    )
    experimental.sort(key=lambda item: str(item.get("id") or item.get("config") or ""))
    _write_json(root / "proxies.json", stable)
    experimental_path = root / "experimental" / "proxies.json"
    if experimental:
        _write_json(experimental_path, experimental)
    else:
        experimental_path.unlink(missing_ok=True)
    return stable, experimental


def _recompute_metadata(
    root: Path, stable: list[dict], experimental: list[dict]
) -> None:
    metadata_path = root / "metadata.json"
    metadata = _load_json(metadata_path)
    if not isinstance(metadata, dict):
        raise SystemExit("release rejected: metadata.json must be an object")

    protocols = Counter(str(item.get("protocol") or "unknown") for item in stable)
    countries = Counter(str(item.get("country_code") or "XX") for item in stable)
    asns = Counter(str(item.get("asn") or "Unknown") for item in stable)
    shielded_candidates = sum(
        1
        for item in experimental
        if isinstance(item.get("details"), dict)
        and bool(item["details"].get("shielded_candidate"))
    )
    shielded_verified = sum(
        1
        for item in stable
        if isinstance(item.get("details"), dict)
        and bool(item["details"].get("shielded_verified"))
    )

    tested = int(metadata.get("total_tested") or metadata.get("tested") or 0)
    if tested <= 0:
        raise SystemExit("release rejected: no proxy test evidence")
    if tested < len(stable):
        raise SystemExit(
            "release rejected: stable record count exceeds tested evidence"
        )

    metadata.update(
        {
            "final_count": len(stable),
            "total_working": len(stable),
            "working": len(stable),
            "total_valid_proxies": len(stable),
            "protocols": dict(sorted(protocols.items())),
            "country_stats": dict(sorted(countries.items())),
            "asns": dict(sorted(asns.items())),
            "experimental_count": len(experimental),
            "shielded_candidate_count": shielded_candidates,
            "shielded_verified_count": shielded_verified,
            "publication_channels": {
                "stable": "proxies.json",
                "experimental": ("experimental/proxies.json" if experimental else None),
            },
        }
    )
    _write_json(metadata_path, metadata)


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--workflow-sha", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--expires-minutes", type=int, default=60)
    args = parser.parse_args()

    if args.expires_minutes <= 0:
        raise SystemExit("expires-minutes must be positive")
    root = args.output_dir.resolve()
    if not root.is_dir():
        raise SystemExit(f"output directory does not exist: {root}")

    _purge_private_state(root)
    (root / "release_manifest.json").unlink(missing_ok=True)
    stable, experimental = _partition_and_normalize_public_records(root)
    _recompute_metadata(root, stable, experimental)

    contract_path = Path(__file__).resolve().parents[1] / "docs" / "output_matrix.json"
    contract = _load_json(contract_path)
    declared = (
        {
            str(item["path"])
            for item in contract.get("outputs", [])
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
        if isinstance(contract, dict)
        else set()
    )
    exact_known = {
        "proxies.json",
        "metadata.json",
        "health.json",
        "format_compatibility.json",
        "artifact_manifest.json",
        "pipeline_events.jsonl",
        ".nojekyll",
    }
    approved_prefixes = (
        "api/",
        "assets/",
        "data/",
        "docs/",
        "evidence/",
        "experimental/",
        "tools/",
    )
    approved_suffixes = {
        ".css",
        ".html",
        ".ico",
        ".js",
        ".json",
        ".jsonl",
        ".map",
        ".md",
        ".png",
        ".svg",
        ".txt",
        ".wasm",
        ".webmanifest",
        ".yaml",
        ".yml",
        ".zip",
    }
    allowed = declared | exact_known
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root).as_posix()
        if (
            rel.startswith(approved_prefixes)
            and path.suffix.lower() in approved_suffixes
        ):
            allowed.add(rel)
    digests = validate_public_artifact(
        root,
        allowed_paths=allowed,
        required_paths={"proxies.json", "metadata.json"},
    )

    policy_material = json.dumps(
        {
            "stable_requires_verified_working": True,
            "experimental_channel_separated": True,
            "fail_on_zero_tested": True,
            "fail_on_zero_working": True,
            "private_state_forbidden": True,
            "credential_scan_enforced": True,
            "source_sha": args.source_sha,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    manifest = write_release_manifest(
        root / "release_manifest.json",
        source_commit_sha=args.source_sha,
        workflow_sha=args.workflow_sha,
        image_digest=args.image_digest,
        policy_digest=_digest_text(policy_material),
        artifact_digests=digests,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=args.expires_minutes),
        parent_release_digest=os.environ.get("PARENT_RELEASE_DIGEST") or None,
    )
    print(manifest["release_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
