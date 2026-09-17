# SPDX-License-Identifier: AGPL-3.0-or-later
"""Enforce the production Pages signing policy for sealed release artifacts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_pages_artifact import (
    _public_key_hex_from_env,
    _validate_manifest_signature,
)

_TRUTHY = {"1", "true", "yes"}


def _allow_unsigned_pages() -> bool:
    return os.environ.get("ALLOW_UNSIGNED_PAGES", "").strip().lower() in _TRUTHY


def validate_pages_signature_policy(root: Path) -> list[str]:
    root = Path(root)
    manifest_path = root / "artifact_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"could not read artifact_manifest.json: {exc}"]
    except json.JSONDecodeError as exc:
        return [f"invalid artifact_manifest.json: {exc}"]
    if not isinstance(manifest, dict):
        return ["artifact_manifest.json must be a JSON object"]

    raw_public_key = (os.environ.get("CS_PUBLIC_KEY") or "").strip()
    public_key_hex = _public_key_hex_from_env()
    signature = manifest.get("manifest_signature")

    if raw_public_key and not public_key_hex:
        return ["CS_PUBLIC_KEY is configured but is not a valid Ed25519 public key"]

    if public_key_hex:
        return _validate_manifest_signature(manifest)

    if signature is not None:
        return [
            "artifact_manifest.json is signed but CS_PUBLIC_KEY is not configured; "
            "signed artifacts must never be accepted without a trust anchor"
        ]

    if not _allow_unsigned_pages():
        return [
            "unsigned Pages publication is disabled by default; configure signing "
            "or explicitly set repository variable ALLOW_UNSIGNED_PAGES=true"
        ]

    return []


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output")
    errors = validate_pages_signature_policy(root)
    if errors:
        print("ERROR: Pages signature policy rejected the artifact", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    mode = "signed" if _public_key_hex_from_env() else "explicit-unsigned"
    print(f"OK: Pages signature policy accepted artifact in {mode} mode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
