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
    explicit_public_key = env.get("CS_PUBLIC_KEY", "").strip()
    signing_key = (
        env.get("CS_SIGNING_PRIVATE_KEY_HEX", "").strip()
        or env.get("CONFIGSTREAM_SIGNING_PRIVATE_KEY_HEX", "").strip()
    )

    public_key = ""
    if explicit_public_key:
        try:
            public_key = _resolve_public_key({"CS_PUBLIC_KEY": explicit_public_key})
        except (TypeError, ValueError):
            errors.append("frontend verification key is not a valid Ed25519 public key")
    elif signing_key:
        try:
            public_key = _resolve_public_key(
                {"CS_SIGNING_PRIVATE_KEY_HEX": signing_key}
            )
        except (TypeError, ValueError):
            errors.append("configured Ed25519 signing key is invalid")
    else:
        errors.append(
            "frontend verification key is unavailable: configure CS_PUBLIC_KEY or "
            "CS_SIGNING_PRIVATE_KEY_HEX"
        )

    normalized_public = normalize_public_key_hex(public_key) if public_key else ""
    if public_key and not normalized_public:
        errors.append("frontend verification key is not a valid Ed25519 public key")

    if explicit_public_key and signing_key:
        try:
            derived_public = _resolve_public_key(
                {"CS_SIGNING_PRIVATE_KEY_HEX": signing_key}
            )
            normalized_derived = normalize_public_key_hex(derived_public)
        except (TypeError, ValueError):
            normalized_derived = ""
            errors.append("configured Ed25519 signing key is invalid")
        if (
            normalized_derived
            and normalized_public
            and normalized_derived != normalized_public
        ):
            errors.append(
                "CS_PUBLIC_KEY does not match the public key derived from "
                "CS_SIGNING_PRIVATE_KEY_HEX"
            )

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
