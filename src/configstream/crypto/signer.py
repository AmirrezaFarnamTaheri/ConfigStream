# SPDX-License-Identifier: AGPL-3.0-or-later
import time
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


class Signer:
    """
    Handles Ed25519 signing and verification of subscription content.
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
            # Ed25519PrivateKey.from_private_bytes expects 32 bytes
            key_bytes = bytes.fromhex(private_key_hex)
            if len(key_bytes) == 64:
                # If full key (seed + pub), take first 32 bytes (seed)
                key_bytes = key_bytes[:32]
            self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key_bytes)

    def sign_subscription(self, content: str) -> Dict[str, Any]:
        """
        Signs the content string.

        Returns:
            Dict containing the content, signature (hex), and timestamp.
        """
        if not self._private_key:
            raise ValueError("Private key not configured for signing.")

        # Sign the content bytes
        content_bytes = content.encode("utf-8")
        signature = self._private_key.sign(content_bytes)

        return {
            "content": content,
            "signature": signature.hex(),
            "timestamp": time.time(),
        }

    @staticmethod
    def verify_signature(content: str, signature_hex: str, public_key_hex: str) -> bool:
        """
        Verifies the signature of the content using the public key.
        """
        try:
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(public_key_hex)
            )
            public_key.verify(bytes.fromhex(signature_hex), content.encode("utf-8"))
            return True
        except (InvalidSignature, ValueError):
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
