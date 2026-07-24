# SPDX-License-Identifier: AGPL-3.0-or-later
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
        max_age_seconds: int = SIGNATURE_MAX_AGE_SECONDS,
    ) -> bool:
        """Verify an artifact manifest's signature and timestamp freshness."""
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
            if age < -CLOCK_SKEW_TOLERANCE_SECONDS or age > max_age_seconds:
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
                       If None the age check is skipped (legacy callers only).
            max_age_seconds: Maximum acceptable age of the signature in seconds.

        Returns:
            True only when the signature is cryptographically valid *and*
            the timestamp is within the acceptable window.
        """
        try:
            # --- Replay / freshness check ----------------------------------------
            if timestamp is not None:
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

            if timestamp is not None:
                # Verify against the same canonical payload used during signing.
                payload = _build_signed_payload(content_bytes, int(timestamp))
            else:
                # Legacy path: signature was produced over raw content bytes only.
                payload = content_bytes

            public_key.verify(bytes.fromhex(signature_hex), payload)
            return True
        except (InvalidSignature, ValueError, struct.error):
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
