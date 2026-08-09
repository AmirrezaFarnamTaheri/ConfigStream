# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fail fast when mandatory release trust inputs are unavailable or malformed."""

from __future__ import annotations

import os
import sys
from typing import Mapping

from configstream.signer import normalize_public_key_hex
from scripts.validate_frontend_placeholders import _resolve_public_key


def validate_release_inputs(env: Mapping[str, str]) -> list[str]:
    errors: list[str] = []
    try:
        public_key = _resolve_public_key(env)
    except (TypeError, ValueError):
        public_key = ""
        errors.append("configured Ed25519 signing key is invalid")

    if not public_key:
        errors.append(
            "frontend verification key is unavailable: configure CS_PUBLIC_KEY or "
            "CS_SIGNING_PRIVATE_KEY_HEX"
        )
    elif not normalize_public_key_hex(public_key):
        errors.append("frontend verification key is not a valid Ed25519 public key")

    return errors


def main() -> int:
    errors = validate_release_inputs(os.environ)
    if errors:
        print("ERROR: release prerequisite validation failed", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("OK: mandatory release trust inputs are available and valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
