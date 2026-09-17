# SPDX-License-Identifier: AGPL-3.0-or-later
"""Enforce the production Pages signing policy for sealed release artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from configstream.signer import Signer, normalize_public_key_hex


def validate_pages_signature_policy(
    root: Path,
    *,
    public_key: str = "",
    allow_unsigned: bool = False,
) -> list[str]:
    """Validate the independent Pages publication trust boundary.

    Artifact generation may be signed or unsigned, but Pages publication is
    fail-closed by default. A signed artifact always requires a configured,
    valid trust anchor. A genuinely unsigned artifact requires an explicit
    publication opt-in supplied by the deployment workflow.
    """

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

    raw_public_key = (public_key or "").strip()
    public_key_hex = normalize_public_key_hex(raw_public_key)
    signature = manifest.get("manifest_signature")

    if raw_public_key and not public_key_hex:
        return ["configured Pages public key is not a valid Ed25519 public key"]

    if public_key_hex:
        if not Signer.verify_manifest_signature(manifest, public_key_hex):
            return ["artifact_manifest.json manifest signature verification failed"]
        return []

    if signature is not None:
        return [
            "artifact_manifest.json is signed but no Pages public key was supplied; "
            "signed artifacts must never be accepted without a trust anchor"
        ]

    if not allow_unsigned:
        return [
            "unsigned Pages publication is disabled by default; configure signing "
            "or explicitly allow unsigned publication"
        ]

    return []


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("output"))
    parser.add_argument(
        "--public-key",
        default="",
        help="Ed25519 public key in a supported raw/SPKI encoding",
    )
    parser.add_argument(
        "--allow-unsigned",
        action="store_true",
        help="explicitly permit publication of a genuinely unsigned artifact",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    errors = validate_pages_signature_policy(
        args.root,
        public_key=args.public_key,
        allow_unsigned=args.allow_unsigned,
    )
    if errors:
        print("ERROR: Pages signature policy rejected the artifact", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    mode = "signed" if args.public_key else "explicit-unsigned"
    print(f"OK: Pages signature policy accepted artifact in {mode} mode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
