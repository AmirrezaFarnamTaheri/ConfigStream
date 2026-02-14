# SPDX-License-Identifier: AGPL-3.0-or-later
# Steganography transport module.

import zlib
import logging
import hmac
import hashlib
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Magic Marker to separate Image from Payload
# We use a distinct byte sequence unlikely to appear in image data
# This is the PRIMARY transport method for ConfigStream v2.0+.
MAGIC_MARKER = b"CSTREAM_PAYLOAD_START>>"


class StegoPacker:
    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize with a Fernet key.
        If None, generates a new one (for dynamic sessions).
        """
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def pack(
        self, cover_image_path: Path, payload_data: str, output_path: Path
    ) -> bool:
        """
        Embeds payload_data into cover_image_path.
        Includes HMAC signature for integrity.
        """
        try:
            # 1. Prepare Payload
            # Compress first
            compressed = zlib.compress(payload_data.encode("utf-8"), level=9)

            # Sign the compressed data (HMAC-SHA256)
            signature = hmac.new(self.key, compressed, hashlib.sha256).digest()

            # Encrypt the compressed data + signature
            # Payload = Encrypt(Signature + CompressedData)
            payload_blob = signature + compressed
            encrypted = self.cipher.encrypt(payload_blob)

            # 2. Read Cover Image
            if not cover_image_path.exists():
                logger.error(f"Cover image not found: {cover_image_path}")
                return False

            with open(cover_image_path, "rb") as f:
                image_bytes = f.read()

            # 3. Fuse (Append-Only Steganography)
            # Image Data + Marker + Encrypted Blob
            final_bytes = image_bytes + MAGIC_MARKER + encrypted

            # 4. Write
            with open(output_path, "wb") as f:
                f.write(final_bytes)

            logger.info(
                f"Stego image created at {output_path} ({len(final_bytes)} bytes)"
            )
            return True

        except Exception as e:
            logger.error(f"Stego packing failed: {e}")
            return False

    def get_key_str(self) -> str:
        return self.key.decode("utf-8")


# Helper for CI integration
def generate_stego_assets(
    config_dir: Path, assets_dir: Path, secret_key: Optional[str] = None
):
    """
    scans output directory for singbox.json and creates image variants.
    """
    config_file = config_dir / "singbox.json"
    if not config_file.exists():
        logger.warning(f"Config file not found: {config_file}")
        return

    # Use a hardcoded key from secrets OR generate one (and print it for the frontend)
    # For Zero-Budget resilience, we usually want a STATIC key hardcoded in the frontend JS.
    # Ensure this key matches what is in frontend/assets/js/stego.js

    # Priority:
    # 1. Passed arg
    # 2. Env var STEGO_KEY (preferred) or CONFIG_STREAM_KEY (fallback)
    # 3. Generate new
    if not secret_key:
        from configstream.config import AppSettings

        settings = AppSettings()
        secret_key = settings.STEGO_KEY or settings.CONFIG_STREAM_KEY

    if secret_key:
        try:
            key = secret_key.encode()
            # Validate the key is a valid Fernet key before using it
            Fernet(key)
        except Exception:
            logger.warning("Invalid STEGO_KEY provided, generating ephemeral key.")
            key = Fernet.generate_key()
    else:
        key = Fernet.generate_key()
        logger.warning(
            "No STEGO_KEY/CONFIG_STREAM_KEY set; using random key for this build."
        )

    packer = StegoPacker(key)

    content = config_file.read_text(encoding="utf-8")

    # Cover images should be in assets_dir
    # We try to find a valid png
    covers = list(assets_dir.glob("*.png"))
    if not covers:
        logger.warning("No cover images found for steganography.")
        return

    # Create a stego version for each cover (redundancy)
    for cover in covers:
        output_name = f"stealth_{cover.name}"
        packer.pack(cover, content, config_dir / output_name)
