# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate optional release-signing inputs before production publication.

Availability contract: the release pipeline must never depend on an optional
secret being present or valid. Signing is *active* only when both halves of the
keypair resolve to a valid, matching pair. Any other combination degrades to
unsigned publication with a recorded note instead of blocking the release, so a
missing, malformed or half-configured secret can never leave the site stale.

The one invariant that does not degrade: a signature is never accepted without a
valid trust anchor, and a signed manifest is never downgraded to unsigned.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from configstream.signer import Signer
from configstream.signing_config import resolve_signing_material


def verify_usable_keypair(material) -> list[str]:
    """Prove the resolved pair can actually sign and verify before publishing."""

    errors: list[str] = []
    if not material.active:
        return errors
    try:
        signer = Signer(material.signing_key)
        manifest: dict = {"schema_version": "1.0", "files": []}
        manifest["manifest_signature"] = signer.sign_manifest(manifest)
    except (TypeError, ValueError) as exc:
        return [f"resolved signing keypair is unusable: {exc}"]
    if not Signer.verify_manifest_signature(manifest, material.public_key):
        errors.append("resolved signing keypair produced an unverifiable signature")
    return errors


def validate_release_inputs(env) -> list[str]:
    """Return only problems that must stop publication.

    Optional key material is deliberately *not* fatal: it degrades to unsigned
    publication instead. Anything reported here is a genuine inability to sign
    with material that resolved cleanly.
    """

    return verify_usable_keypair(resolve_signing_material(env))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--print-signing-configured",
        action="store_true",
        help="print 'true' when a usable signing keypair is configured",
    )
    args = parser.parse_args()

    material = resolve_signing_material(os.environ)
    for note in material.notes:
        print(f"WARN: {note}", file=sys.stderr)

    if args.print_signing_configured:
        print("true" if material.active else "false")
        return 0

    errors = validate_release_inputs(os.environ)
    if errors:
        print("ERROR: release prerequisite validation failed", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(
        f"OK: release signing is {material.state}; publication does not depend on "
        "optional secrets."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
