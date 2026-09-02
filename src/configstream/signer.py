# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import binascii
import hashlib
import json
import struct
import time
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

# Maximum age (seconds) of a valid signed payload.
SIGNATURE_MAX_AGE_SECONDS: int = 300  # 5 minutes

# Tolerance for NTP clock drift between signer and verifier hosts.
CLOCK_SKEW_TOLERANCE_SECONDS: int = 30


def normalize_public_key_hex(value: str) -> str:
    """Normalize a supported Ed25519 public-key encoding to raw hex.

    Browser deployment uses Base64-encoded SPKI, while Python verification
    consumes the 32-byte raw key.  Keeping the conversion here prevents the
    release validator and rollback snapshotter from implementing different
    trust rules.
    """

    candidate = (value or "").strip()
    if not candidate or "PLACEHOLDER" in candidate or "79e/79e/" in candidate:
        return ""

    try:
        key_bytes = base64.b64decode(candidate, validate=True)
    except (ValueError, binascii.Error):
        key_bytes = b""

    if key_bytes:
        try:
            parsed = serialization.load_der_public_key(key_bytes)
            if isinstance(parsed, ed25519.Ed25519PublicKey):
                return parsed.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                ).hex()
        except (ValueError, TypeError):
            pass
        if len(key_bytes) == 32:
            try:
                ed25519.Ed25519PublicKey.from_public_bytes(key_bytes)
            except ValueError:
                pass
            else:
                return key_bytes.hex()

    try:
        raw = bytes.fromhex(candidate)
    except ValueError:
        return ""
    if len(raw) != 32:
        return ""
    try:
        ed25519.Ed25519PublicKey.from_public_bytes(raw)
    except ValueError:
        return ""
    return raw.hex()


def _build_signed_payload(content_bytes: bytes, timestamp_int: int) -> bytes:
    """Return the canonical byte string that is actually signed/verified."""
    return struct.pack(">Q", timestamp_int) + content_bytes


def _canonical_manifest_payload(manifest: Dict[str, Any], timestamp_int: int) -> bytes:
    """Return canonical JSON bytes prefixed with big-endian uint64 timestamp."""
    canonical_json = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return _build_signed_payload(canonical_json, timestamp_int)


class Signer:
    """
    Handles Ed25519 signing and verification of subscription content.

    Replay protection
    -----------------
    The timestamp is included *inside* the signed payload so that the
    cryptographic signature covers both the content and the time it was issued.
    ``verify_signature`` additionally checks that the timestamp is within
    ``SIGNATURE_MAX_AGE_SECONDS`` of the current time.
    """

    def __init__(self, private_key_hex: Optional[str] = None):
        """
        Initialize the Signer.

        Args:
            private_key_hex: Hex-encoded private key (64 bytes / 32 bytes seed).
                             If None, signing operations will fail.
        """
        self._private_key = None
        if private_key_hex:
            if not isinstance(private_key_hex, str) or len(private_key_hex) % 2 != 0:
                raise ValueError(
                    "Private key must be a valid hex string with even length"
                )
            # Ed25519PrivateKey.from_private_bytes expects 32 bytes
            key_bytes = bytes.fromhex(private_key_hex)
            if len(key_bytes) == 64:
                # If full key (seed + pub), take first 32 bytes (seed)
                key_bytes = key_bytes[:32]
            elif len(key_bytes) != 32:
                raise ValueError(
                    f"Private key must be 32 or 64 bytes (got {len(key_bytes)})"
                )
            self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key_bytes)

    def sign_subscription(self, content: str) -> Dict[str, Any]:
        """Sign the content string with an embedded timestamp.

        The timestamp is incorporated into the signed payload so the signature
        cannot be replayed after the ``SIGNATURE_MAX_AGE_SECONDS`` window expires.

        Returns:
            Dict containing the content, signature (hex), and timestamp (int seconds).
        """
        if not self._private_key:
            raise ValueError("Private key not configured for signing.")

        timestamp_int = int(time.time())
        content_bytes = content.encode("utf-8")
        payload = _build_signed_payload(content_bytes, timestamp_int)
        signature = self._private_key.sign(payload)

        return {
            "content": content,
            "signature": signature.hex(),
            # Integer seconds so the verifier can round-trip via struct.pack(">Q").
            "timestamp": timestamp_int,
        }

    def sign_manifest(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Sign an artifact manifest dictionary with Ed25519 and timestamp.

        Returns a manifest_signature dictionary to attach to the manifest.
        """
        if not self._private_key:
            raise ValueError("Private key not configured for signing.")

        timestamp_int = int(time.time())
        payload = dict(manifest)
        payload.pop("manifest_signature", None)

        canonical_bytes = _canonical_manifest_payload(payload, timestamp_int)
        signature_bytes = self._private_key.sign(canonical_bytes)

        public_key_bytes = bytes.fromhex(self.get_public_key_hex())
        key_id = hashlib.sha256(public_key_bytes).hexdigest()[:16]

        return {
            "algorithm": "ed25519",
            "signature": signature_bytes.hex(),
            "key_id": f"sha256:{key_id}",
            "timestamp": timestamp_int,
        }

    @staticmethod
    def verify_manifest_signature(
        manifest: Dict[str, Any],
        public_key_hex: str,
        max_age_seconds: Optional[int] = None,
    ) -> bool:
        """Verify an artifact manifest signature.

        A Pages manifest is a static, signed release record.  Its freshness is
        governed by the signed metadata generation time, not by the instant the
        signature was created: a short signature TTL would invalidate every
        otherwise-valid published artifact and rollback snapshot.  Callers that
        need a short-lived token can opt in through ``max_age_seconds``.
        """
        try:
            sig_info = manifest.get("manifest_signature")
            if not isinstance(sig_info, dict):
                return False

            if sig_info.get("algorithm") != "ed25519":
                return False

            signature_hex = sig_info.get("signature")
            if not isinstance(signature_hex, str):
                return False

            key_id = sig_info.get("key_id")
            pub_bytes = bytes.fromhex(public_key_hex)
            expected_key_id = f"sha256:{hashlib.sha256(pub_bytes).hexdigest()[:16]}"
            if key_id != expected_key_id:
                return False

            timestamp = sig_info.get("timestamp")
            if timestamp is None:
                return False
            timestamp_int = int(timestamp)
            if timestamp_int < 0:
                return False

            age = int(time.time()) - timestamp_int
            if age < -CLOCK_SKEW_TOLERANCE_SECONDS:
                return False
            if max_age_seconds is not None and age > max_age_seconds:
                return False

            payload = dict(manifest)
            payload.pop("manifest_signature", None)

            canonical_bytes = _canonical_manifest_payload(payload, timestamp_int)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            public_key.verify(bytes.fromhex(signature_hex), canonical_bytes)
            return True
        except (InvalidSignature, ValueError, TypeError, struct.error):
            return False

    @staticmethod
    def verify_subscription(
        content: str,
        signature_hex: str,
        public_key_hex: str,
        timestamp: Optional[int] = None,
        max_age_seconds: int = SIGNATURE_MAX_AGE_SECONDS,
    ) -> bool:
        """Verify the Ed25519 subscription signature and enforce replay protection.

        Alias for verify_signature for semantic parity with sign_subscription.
        """
        return Signer.verify_signature(
            content=content,
            signature_hex=signature_hex,
            public_key_hex=public_key_hex,
            timestamp=timestamp,
            max_age_seconds=max_age_seconds,
        )

    @staticmethod
    def verify_signature(
        content: str,
        signature_hex: str,
        public_key_hex: str,
        timestamp: Optional[int] = None,
        max_age_seconds: int = SIGNATURE_MAX_AGE_SECONDS,
    ) -> bool:
        """Verify the Ed25519 signature and enforce the replay-protection window.

        Args:
            content: The original content string.
            signature_hex: Hex-encoded Ed25519 signature.
            public_key_hex: Hex-encoded 32-byte Ed25519 public key.
            timestamp: Integer seconds (UTC) that was embedded when signing.
                       Required: every signature produced by this class embeds
                       one, so ``None`` is treated as malformed input and is
                       rejected outright. It remains ``Optional`` in the
                       signature only so that callers forwarding a missing
                       field fail closed (``False``) instead of raising.
            max_age_seconds: Maximum acceptable age of the signature in seconds.

        Returns:
            True only when a timestamp is supplied, the signature is
            cryptographically valid, *and* the timestamp is within the
            acceptable window. False in every other case.
        """
        try:
            # --- Replay / freshness check ----------------------------------------
            # Fail closed when no timestamp is supplied: a signature verified over
            # raw content with no age binding would be replayable forever. Every
            # signature this class produces embeds a timestamp, so a missing one
            # is a malformed/legacy input, not a valid case.
            if timestamp is None:
                return False
            age = int(time.time()) - int(timestamp)
            # Allow up to CLOCK_SKEW_TOLERANCE_SECONDS of negative age to
            # tolerate normal NTP drift between signer and verifier hosts.
            # Clearly future timestamps (beyond tolerance) are still rejected.
            if age < -CLOCK_SKEW_TOLERANCE_SECONDS or age > max_age_seconds:
                return False

            # --- Cryptographic verification --------------------------------------
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(public_key_hex)
            )
            content_bytes = content.encode("utf-8")

            # Verify against the same canonical payload used during signing.
            payload = _build_signed_payload(content_bytes, int(timestamp))

            public_key.verify(bytes.fromhex(signature_hex), payload)
            return True
        except (InvalidSignature, TypeError, ValueError, struct.error):
            return False

    def get_public_key_hex(self) -> str:
        """Returns the public key in hex format."""
        if not self._private_key:
            raise ValueError("Private key not configured.")
        public_key = self._private_key.public_key()
        raw_bytes: bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        return raw_bytes.hex()
