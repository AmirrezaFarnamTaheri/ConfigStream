# SPDX-License-Identifier: AGPL-3.0-or-later
"""Finalize a shard's public artifact contract after wrapper-owned mutations."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from configstream.output_logic import write_public_artifact_contract
from configstream.signer import Signer
from configstream.utils import AtomicFileWriter

from configstream.constants import ARTIFACT_TRANSIENT_SUFFIXES as TRANSIENT_SUFFIXES


def prune_transient_files(output_dir: Path) -> list[str]:
    """Remove process-local files that must never become uploaded shard evidence."""

    removed: list[str] = []
    if not output_dir.is_dir():
        raise FileNotFoundError(f"shard output directory does not exist: {output_dir}")
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or not path.name.endswith(TRANSIENT_SUFFIXES):
            continue
        rel_path = path.relative_to(output_dir).as_posix()
        path.unlink()
        removed.append(rel_path)
    return removed


def _drop_transient_manifest_entries(manifest: dict[str, object]) -> None:
    raw_files = manifest.get("files", [])
    if not isinstance(raw_files, list):
        raise ValueError("artifact manifest files must be a list")
    files = [
        item
        for item in raw_files
        if isinstance(item, dict)
        and isinstance(item.get("path"), str)
        and not str(item["path"]).endswith(TRANSIENT_SUFFIXES)
    ]
    manifest["files"] = files
    manifest["file_count"] = len(files)
    manifest["total_size_bytes"] = sum(
        int(item.get("size_bytes", 0) or 0) for item in files
    )


def _rewrite_filtered_manifest(output_dir: Path, manifest: dict[str, object]) -> None:
    from configstream.signing_config import resolve_signing_material

    had_signature = isinstance(manifest.pop("manifest_signature", None), dict)
    _drop_transient_manifest_entries(manifest)
    if had_signature:
        # Availability over strictness: with no usable keypair the refreshed
        # manifest is published unsigned rather than failing the refresh. The
        # stale signature was already removed, so it can never be carried forward.
        signing_key = resolve_signing_material(os.environ).signing_key
        if signing_key:
            manifest["manifest_signature"] = Signer(signing_key).sign_manifest(manifest)
        else:
            print(
                "WARN: refreshed shard manifest published unsigned: no usable "
                "signing keypair",
                file=sys.stderr,
            )
    AtomicFileWriter.write_text(
        output_dir / "artifact_manifest.json",
        json.dumps(manifest, indent=2, ensure_ascii=False),
    )


def refresh_shard_contract(output_dir: Path) -> dict[str, object]:
    """Hash the final shard state and remove transient lock evidence.

    ``write_public_artifact_contract`` refreshes mutable lineage/event hashes after
    the pipeline process exits. Atomic writes create lock files while doing so, so
    the final filtering pass removes those process-local files and their manifest
    entries without weakening hashes for the stable artifacts.
    """

    prune_transient_files(output_dir)
    manifest = write_public_artifact_contract(output_dir)
    _rewrite_filtered_manifest(output_dir, manifest)
    prune_transient_files(output_dir)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    manifest = refresh_shard_contract(args.output_dir)
    print(
        "OK: refreshed shard artifact contract "
        f"({manifest.get('file_count', 0)} governed files)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
