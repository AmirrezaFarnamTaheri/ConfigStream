# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from scripts.preflight_release_inputs import validate_release_inputs


def test_preflight_accepts_public_key_derived_from_signing_key() -> None:
    assert validate_release_inputs({"CS_SIGNING_PRIVATE_KEY_HEX": "01" * 32}) == []


def test_preflight_rejects_missing_release_trust_anchor() -> None:
    errors = validate_release_inputs({})
    assert any("verification key is unavailable" in error for error in errors)


def test_preflight_rejects_malformed_explicit_public_key() -> None:
    errors = validate_release_inputs({"CS_PUBLIC_KEY": "not-an-ed25519-key"})
    assert any("not a valid Ed25519 public key" in error for error in errors)
