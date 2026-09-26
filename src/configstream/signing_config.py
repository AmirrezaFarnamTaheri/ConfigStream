# SPDX-License-Identifier: AGPL-3.0-or-later
"""Availability-first resolution of the optional Ed25519 signing keypair.

The release pipeline must never depend on an optional secret being present or
valid. Signing is *active* only when both halves resolve to a valid, matching
pair. Every other combination degrades to unsigned publication with a recorded
note, so a missing, malformed or half-configured secret can never leave the
public site stale.

The invariant that does not degrade lives elsewhere and still holds: a signature
is never accepted without a valid trust anchor, and a signed manifest is never
downgraded to unsigned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .signer import normalize_public_key_hex

SIGNING_ACTIVE = "signed"
SIGNING_DEGRADED = "unsigned"


@dataclass(frozen=True)
class SigningMaterial:
    """Outcome of resolving the optional signing keypair from an environment."""

    signing_key: str = ""
    public_key: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def active(self) -> bool:
        """True only when a usable, matching keypair resolved."""

        return bool(self.signing_key and self.public_key)

    @property
    def state(self) -> str:
        return SIGNING_ACTIVE if self.active else SIGNING_DEGRADED


def _normalize_signing_key(value: str) -> str:
    """Return usable Ed25519 seed hex, or an empty string."""

    candidate = (value or "").strip()
    if not candidate or len(candidate) % 2 != 0:
        return ""
    try:
        key_bytes = bytes.fromhex(candidate)
    except ValueError:
        return ""
    if len(key_bytes) == 64:
        key_bytes = key_bytes[:32]
    if len(key_bytes) != 32:
        return ""
    return candidate


def resolve_signing_material(env: Mapping[str, str]) -> SigningMaterial:
    """Return the usable keypair, or a degraded empty pair plus notes.

    The notes explain *why* signing is inactive so release evidence records the
    reason instead of publishing an unsigned artifact without explanation.
    """

    raw_public_key = (env.get("CS_PUBLIC_KEY") or "").strip()
    raw_signing_key = (env.get("CS_SIGNING_PRIVATE_KEY_HEX") or "").strip()
    if not raw_signing_key:
        raw_signing_key = (
            env.get("CONFIGSTREAM_SIGNING_PRIVATE_KEY_HEX") or ""
        ).strip()

    if not raw_public_key and not raw_signing_key:
        return SigningMaterial(
            notes=["no signing key configured; publishing unsigned by policy"]
        )

    notes: list[str] = []
    signing_key = _normalize_signing_key(raw_signing_key)
    if raw_signing_key and not signing_key:
        notes.append(
            "CS_SIGNING_PRIVATE_KEY_HEX is not a valid Ed25519 key; ignoring it"
        )

    derived_public_key = ""
    if signing_key:
        from .signer import Signer

        try:
            derived_public_key = normalize_public_key_hex(
                Signer(signing_key).get_public_key_hex()
            )
        except (TypeError, ValueError):
            derived_public_key = ""

    if not raw_public_key:
        if not derived_public_key:
            return SigningMaterial(notes=notes)
        # A usable private key with no explicit anchor is a valid configuration:
        # the anchor is derived from the key itself.
        return SigningMaterial(
            signing_key=signing_key, public_key=derived_public_key, notes=notes
        )

    public_key = normalize_public_key_hex(raw_public_key)
    if not public_key:
        notes.append("CS_PUBLIC_KEY is not a valid Ed25519 public key; ignoring it")
        return SigningMaterial(notes=notes)

    if not derived_public_key:
        notes.append(
            "CS_PUBLIC_KEY has no usable signing key; ignoring the trust anchor and "
            "publishing unsigned"
        )
        return SigningMaterial(notes=notes)

    if derived_public_key != public_key:
        notes.append(
            "CS_PUBLIC_KEY does not match the public key derived from "
            "CS_SIGNING_PRIVATE_KEY_HEX; ignoring both and publishing unsigned"
        )
        return SigningMaterial(notes=notes)

    return SigningMaterial(signing_key=signing_key, public_key=public_key, notes=notes)


def usable_signing_key(env: Mapping[str, str]) -> str:
    """Return the signing seed only when the whole keypair is usable."""

    return resolve_signing_material(env).signing_key
