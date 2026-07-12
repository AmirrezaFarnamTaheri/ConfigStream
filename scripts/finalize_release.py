#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sanitize, validate, and identify one immutable public release directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from configstream.publication import validate_public_artifact, write_release_manifest


PRIVATE_NAMES = {
    "test_cache.json",
    "source_quality.db",
    "anomaly.db",
    "history.db",
    "pipeline_events.jsonl",
    "consolidated_pipeline.log",
}
PRIVATE_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".log", ".lock", ".tmp"}


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


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid required JSON file {path}: {exc}") from exc


def _require_viable_release(root: Path) -> None:
    proxies = _load_json(root / "proxies.json")
    metadata = _load_json(root / "metadata.json")
    if not isinstance(proxies, list) or not proxies:
        raise SystemExit("release rejected: proxies.json must be a non-empty list")
    if not isinstance(metadata, dict):
        raise SystemExit("release rejected: metadata.json must be an object")
    tested = int(metadata.get("total_tested", metadata.get("tested", 0)) or 0)
    working = int(metadata.get("total_working", metadata.get("working", 0)) or 0)
    if tested <= 0:
        raise SystemExit("release rejected: no proxy test evidence")
    if working <= 0:
        raise SystemExit("release rejected: no working proxy evidence")
    if working > len(proxies):
        raise SystemExit("release rejected: working count exceeds public records")


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

    # Nothing may mutate the public tree after this sequence completes.
    _purge_private_state(root)
    _require_viable_release(root)
    (root / "release_manifest.json").unlink(missing_ok=True)

    allowed = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    digests = validate_public_artifact(
        root,
        allowed_paths=allowed,
        required_paths={"proxies.json", "metadata.json"},
    )

    policy_material = json.dumps(
        {
            "fail_on_zero_tested": True,
            "fail_on_zero_working": True,
            "private_state_forbidden": True,
            "secret_scan_required": True,
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
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=args.expires_minutes),
        parent_release_digest=os.environ.get("PARENT_RELEASE_DIGEST") or None,
    )
    print(manifest["release_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
