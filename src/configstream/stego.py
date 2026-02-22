# SPDX-License-Identifier: AGPL-3.0-or-later
# Steganography transport module.
# Implements robust LSB (Least Significant Bit) Embedding.

import zlib
import logging
import hmac
import hashlib
import struct
from pathlib import Path
from typing import Optional, Tuple
from cryptography.fernet import Fernet

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

logger = logging.getLogger(__name__)

class StegoPacker:
    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize with a Fernet key.
        """
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def pack(
        self, cover_image_path: Path, payload_data: str, output_path: Path
    ) -> bool:
        """
        Embeds payload_data into cover_image_path using LSB steganography.
        Payload = Encrypt(Signature + CompressedData)
        Format: [Length: 4 bytes][Payload Bytes] distributed in LSBs.
        """
        if not PILLOW_AVAILABLE:
            logger.error("Pillow library not found. Cannot perform LSB steganography.")
            return False

        try:
            # 1. Prepare Payload
            compressed = zlib.compress(payload_data.encode("utf-8"), level=9)
            signature = hmac.new(self.key, compressed, hashlib.sha256).digest()
            payload_blob = signature + compressed
            encrypted = self.cipher.encrypt(payload_blob)

            # Prepend 4-byte length
            final_payload = struct.pack(">I", len(encrypted)) + encrypted

            # 2. Read Image
            img = Image.open(cover_image_path)
            img = img.convert("RGB") # Ensure RGB
            pixels = img.load()
            width, height = img.size

            # Check capacity (3 bits per pixel)
            max_bytes = (width * height * 3) // 8
            if len(final_payload) > max_bytes:
                logger.error(f"Payload too large for image ({len(final_payload)} > {max_bytes})")
                return False

            # 3. Embed LSB
            data_index = 0
            bit_index = 0
            payload_bits = []

            # Convert payload to bits
            for byte in final_payload:
                for i in range(7, -1, -1):
                    payload_bits.append((byte >> i) & 1)

            total_bits = len(payload_bits)
            idx = 0

            for y in range(height):
                for x in range(width):
                    if idx >= total_bits:
                        break

                    r, g, b = pixels[x, y]

                    # Embed in R
                    if idx < total_bits:
                        r = (r & ~1) | payload_bits[idx]
                        idx += 1
                    # Embed in G
                    if idx < total_bits:
                        g = (g & ~1) | payload_bits[idx]
                        idx += 1
                    # Embed in B
                    if idx < total_bits:
                        b = (b & ~1) | payload_bits[idx]
                        idx += 1

                    pixels[x, y] = (r, g, b)
                if idx >= total_bits:
                    break

            img.save(output_path, "PNG")
            logger.info(f"Stego (LSB) image created at {output_path}")
            return True

        except Exception as e:
            logger.error(f"Stego packing failed: {e}")
            return False

    def unpack(self, stego_image_path: Path) -> Optional[str]:
        """
        Extracts and decrypts payload from LSB stego image.
        """
        if not PILLOW_AVAILABLE:
            return None

        try:
            img = Image.open(stego_image_path)
            img = img.convert("RGB")
            pixels = img.load()
            width, height = img.size

            # Extract bits
            bits = []
            # Optimization: We only need to read 32 bits first to get length
            # But simpler to stream.

            # Helper to read N bits
            def read_bits(n):
                res_bits = []
                count = 0
                for y in range(height):
                    for x in range(width):
                        r, g, b = pixels[x, y]
                        for val in (r, g, b):
                            res_bits.append(val & 1)
                            count += 1
                            if count >= n:
                                return res_bits
                return res_bits

            # Read Length (32 bits = 4 bytes)
            # We assume the embedding starts at 0,0.
            # Ideally we need stateful reading.

            extracted_bytes = bytearray()
            byte_val = 0
            bit_count = 0

            # Limit extraction to prevent memory issues?
            # Max possible size.

            length = 0
            header_found = False

            for y in range(height):
                for x in range(width):
                    r, g, b = pixels[x, y]
                    for val in (r, g, b):
                        bit = val & 1
                        byte_val = (byte_val << 1) | bit
                        bit_count += 1

                        if bit_count == 8:
                            extracted_bytes.append(byte_val)
                            byte_val = 0
                            bit_count = 0

                            if not header_found and len(extracted_bytes) == 4:
                                length = struct.unpack(">I", extracted_bytes)[0]
                                extracted_bytes = bytearray() # Reset buffer for payload
                                header_found = True

                            if header_found and len(extracted_bytes) == length:
                                raise StopIteration # Done
                if header_found and len(extracted_bytes) == length:
                    break

        except StopIteration:
            pass
        except Exception as e:
            logger.error(f"Stego unpack error: {e}")
            return None

        if not header_found or len(extracted_bytes) != length:
            return None

        try:
            # Decrypt
            decrypted = self.cipher.decrypt(bytes(extracted_bytes))
            # Split signature
            signature = decrypted[:32] # SHA256 digest size
            compressed = decrypted[32:]

            # Verify HMAC
            expected_sig = hmac.new(self.key, compressed, hashlib.sha256).digest()
            if signature != expected_sig:
                logger.error("Stego signature mismatch")
                return None

            return zlib.decompress(compressed).decode("utf-8")
        except Exception as e:
            logger.error(f"Stego decryption failed: {e}")
            return None

def generate_stego_assets(
    config_dir: Path, assets_dir: Path, secret_key: Optional[str] = None
):
    """
    Scans output directory for singbox.json and creates image variants.
    """
    config_file = config_dir / "singbox.json"
    if not config_file.exists():
        return

    if not secret_key:
        from configstream.config import AppSettings
        settings = AppSettings()
        secret_key = settings.STEGO_KEY or settings.CONFIG_STREAM_KEY

    if secret_key:
        try:
            key = secret_key.encode()
            Fernet(key)
        except Exception:
            key = Fernet.generate_key()
    else:
        key = Fernet.generate_key()

    packer = StegoPacker(key)
    content = config_file.read_text(encoding="utf-8")
    covers = list(assets_dir.glob("*.png"))

    for cover in covers:
        output_name = f"stealth_{cover.name}"
        packer.pack(cover, content, config_dir / output_name)
