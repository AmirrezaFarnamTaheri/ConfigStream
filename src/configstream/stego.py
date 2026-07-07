# SPDX-License-Identifier: AGPL-3.0-or-later
"""Steganography transport module (PNG LSB + Fernet payload)."""

from __future__ import annotations

import binascii
import hashlib
import logging
import math
import struct
import zlib
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

from .utils import AtomicFileWriter

logger = logging.getLogger(__name__)

# Legacy marker kept for backward-compatible extraction of old artifacts.
MAGIC_MARKER = b"CSTREAM_PAYLOAD_START>>"

# New LSB payload framing.
LSB_MAGIC = b"CSP2"
LSB_VERSION = 1
LSB_HEADER_SIZE = 8  # magic(4) + version(1) + reserved(1) + token_len(2)

_PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _crc32(chunk_type: bytes, data: bytes) -> int:
    return binascii.crc32(chunk_type + data) & 0xFFFFFFFF


def _pack_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", _crc32(chunk_type, data))
    )


def _paeth_predictor(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter_png(raw: bytes, width: int, height: int, bpp: int) -> bytearray:
    row_size = width * bpp
    expected = (row_size + 1) * height
    if len(raw) != expected:
        raise ValueError("Invalid PNG scanline buffer size")

    out = bytearray(height * row_size)
    prev_row = bytearray(row_size)

    for y in range(height):
        src_row_start = y * (row_size + 1)
        filt = raw[src_row_start]
        src = raw[src_row_start + 1 : src_row_start + 1 + row_size]
        dst_row_start = y * row_size
        dst = out[dst_row_start : dst_row_start + row_size]

        if filt == 0:  # None
            dst[:] = src
        elif filt == 1:  # Sub
            for i in range(row_size):
                left = dst[i - bpp] if i >= bpp else 0
                dst[i] = (src[i] + left) & 0xFF
        elif filt == 2:  # Up
            for i in range(row_size):
                dst[i] = (src[i] + prev_row[i]) & 0xFF
        elif filt == 3:  # Average
            for i in range(row_size):
                left = dst[i - bpp] if i >= bpp else 0
                up = prev_row[i]
                dst[i] = (src[i] + ((left + up) // 2)) & 0xFF
        elif filt == 4:  # Paeth
            for i in range(row_size):
                left = dst[i - bpp] if i >= bpp else 0
                up = prev_row[i]
                up_left = prev_row[i - bpp] if i >= bpp else 0
                dst[i] = (src[i] + _paeth_predictor(left, up, up_left)) & 0xFF
        else:
            raise ValueError(f"Unsupported PNG filter type: {filt}")

        out[dst_row_start : dst_row_start + row_size] = dst
        prev_row[:] = dst

    return out


def _filter_none(raw_pixels: bytes, width: int, height: int, bpp: int) -> bytes:
    row_size = width * bpp
    out = bytearray((row_size + 1) * height)
    for y in range(height):
        dst_row_start = y * (row_size + 1)
        src_row_start = y * row_size
        out[dst_row_start] = 0  # filter type None
        out[dst_row_start + 1 : dst_row_start + 1 + row_size] = raw_pixels[
            src_row_start : src_row_start + row_size
        ]
    return bytes(out)


def _derive_offsets(
    key_material: bytes, carrier_len: int, *, _nonce: bytes = b""
) -> tuple[int, int]:
    if carrier_len <= 0:
        raise ValueError("carrier_len must be positive")
    # Mix key + carrier_len + optional nonce so that embedding positions are
    # unique per carrier image even when the same key is reused.  Without
    # carrier_len in the hash, every image with the same key would embed
    # bits at identical pixel positions, which is a correlatable fingerprint.
    digest = hashlib.sha256(
        key_material + carrier_len.to_bytes(8, "big") + _nonce
    ).digest()
    start = int.from_bytes(digest[:8], "big") % carrier_len
    stride = (int.from_bytes(digest[8:16], "big") % carrier_len) | 1
    stride = max(1, stride)
    while math.gcd(stride, carrier_len) != 1:
        stride = (stride + 2) % carrier_len
        if stride == 0:
            stride = 1
    return start, stride


def _read_png(
    png_bytes: bytes,
) -> tuple[int, int, int, list[tuple[bytes, bytes]], bytes]:
    if not png_bytes.startswith(_PNG_SIG):
        raise ValueError("Not a PNG file")

    pos = len(_PNG_SIG)
    chunks: list[tuple[bytes, bytes]] = []
    idat_parts: list[bytes] = []
    width = 0
    height = 0
    bpp = 0

    while pos + 8 <= len(png_bytes):
        length = struct.unpack(">I", png_bytes[pos : pos + 4])[0]
        chunk_type = png_bytes[pos + 4 : pos + 8]
        data_start = pos + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end > len(png_bytes):
            raise ValueError("Truncated PNG chunk")
        chunk_data = png_bytes[data_start:data_end]
        chunks.append((chunk_type, chunk_data))
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filt, interlace = (
                struct.unpack(">IIBBBBB", chunk_data)
            )
            if bit_depth != 8 or interlace != 0 or compression != 0 or filt != 0:
                raise ValueError("Unsupported PNG format for stego packing")
            if color_type == 2:  # RGB
                bpp = 3
            elif color_type == 6:  # RGBA
                bpp = 4
            else:
                raise ValueError("Unsupported PNG color type for stego packing")
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break
        pos = crc_end

    if width <= 0 or height <= 0 or bpp <= 0 or not idat_parts:
        raise ValueError("Invalid PNG structure for stego packing")

    return width, height, bpp, chunks, b"".join(idat_parts)


def _build_carrier_positions(width: int, height: int, bpp: int) -> list[int]:
    row_size = width * bpp
    positions: list[int] = []
    for y in range(height):
        row_base = y * row_size
        for x in range(width):
            px_base = row_base + (x * bpp)
            positions.extend((px_base, px_base + 1, px_base + 2))  # RGB channels only
    return positions


def _embed_bytes_into_positions(
    raw_pixels: bytearray,
    positions: list[int],
    payload: bytes,
    key_material: bytes,
) -> None:
    needed_bits = len(payload) * 8
    if needed_bits > len(positions):
        raise ValueError(
            f"Payload too large for cover image capacity ({needed_bits} bits > {len(positions)} bits)"
        )
    start, stride = _derive_offsets(key_material, len(positions))
    for bit_index in range(needed_bits):
        byte_index = bit_index // 8
        bit_pos = 7 - (bit_index % 8)
        bit_value = (payload[byte_index] >> bit_pos) & 1
        pos_index = (start + (bit_index * stride)) % len(positions)
        raw_index = positions[pos_index]
        raw_pixels[raw_index] = (raw_pixels[raw_index] & 0xFE) | bit_value


def _extract_bytes_from_positions(
    raw_pixels: bytes,
    positions: list[int],
    out_len: int,
    key_material: bytes,
) -> bytes:
    needed_bits = out_len * 8
    if needed_bits > len(positions):
        raise ValueError("Requested payload length exceeds carrier capacity")
    start, stride = _derive_offsets(key_material, len(positions))
    out = bytearray(out_len)
    for bit_index in range(needed_bits):
        pos_index = (start + (bit_index * stride)) % len(positions)
        raw_index = positions[pos_index]
        bit_value = raw_pixels[raw_index] & 1
        byte_index = bit_index // 8
        out[byte_index] = (out[byte_index] << 1) | bit_value
    return bytes(out)


def _replace_idat(chunks: list[tuple[bytes, bytes]], new_idat: bytes) -> bytes:
    out = bytearray(_PNG_SIG)
    idat_written = False
    for chunk_type, chunk_data in chunks:
        if chunk_type == b"IDAT":
            if not idat_written:
                out.extend(_pack_chunk(b"IDAT", new_idat))
                idat_written = True
            continue
        out.extend(_pack_chunk(chunk_type, chunk_data))
    if not idat_written:
        raise ValueError("PNG did not contain IDAT chunk")
    return bytes(out)


class StegoPacker:
    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize with a Fernet key.
        If None, generates a new one (for dynamic sessions).
        """
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def _build_payload_blob(self, payload_data: str) -> bytes:
        compressed = zlib.compress(payload_data.encode("utf-8"), level=9)
        # Fernet already applies encrypt-then-MAC semantics; no redundant custom signature.
        token = self.cipher.encrypt(compressed)
        if len(token) > 0xFFFF:
            raise ValueError("Stego token exceeds header size limit")
        header = LSB_MAGIC + bytes([LSB_VERSION, 0]) + struct.pack(">H", len(token))
        return header + token

    def _pack_lsb_png(self, cover_image_path: Path, payload_blob: bytes) -> bytes:
        png_bytes = cover_image_path.read_bytes()
        width, height, bpp, chunks, idat_data = _read_png(png_bytes)
        raw = zlib.decompress(idat_data)
        pixels = _unfilter_png(raw, width, height, bpp)

        positions = _build_carrier_positions(width, height, bpp)
        _embed_bytes_into_positions(pixels, positions, payload_blob, self.key)

        filtered = _filter_none(bytes(pixels), width, height, bpp)
        recompressed = zlib.compress(filtered, level=9)
        return _replace_idat(chunks, recompressed)

    def pack(
        self, cover_image_path: Path, payload_data: str, output_path: Path
    ) -> bool:
        """
        Embed payload_data into PNG pixels using LSB placement derived from SHA-256(key).
        """
        try:
            if not cover_image_path.exists():
                logger.error(f"Cover image not found: {cover_image_path}")
                return False

            payload_blob = self._build_payload_blob(payload_data)
            final_bytes = self._pack_lsb_png(cover_image_path, payload_blob)
            # Atomic write (temp + fsync + rename) so a crash mid-write can't
            # leave a truncated/corrupt PNG at the output path.
            AtomicFileWriter.write_bytes(output_path, final_bytes)
            logger.info(
                "Stego image created at %s (%d bytes, LSB mode)",
                output_path,
                len(final_bytes),
            )
            return True
        except Exception as e:
            logger.error(f"Stego packing failed: {e}")
            return False

    def _unpack_lsb_png(self, image_path: Path) -> str:
        png_bytes = image_path.read_bytes()
        width, height, bpp, _chunks, idat_data = _read_png(png_bytes)
        raw = zlib.decompress(idat_data)
        pixels = _unfilter_png(raw, width, height, bpp)

        positions = _build_carrier_positions(width, height, bpp)
        header = _extract_bytes_from_positions(
            bytes(pixels), positions, LSB_HEADER_SIZE, self.key
        )
        if header[:4] != LSB_MAGIC:
            raise ValueError("LSB stego marker not found")
        version = header[4]
        if version != LSB_VERSION:
            raise ValueError(f"Unsupported stego payload version: {version}")
        token_len = struct.unpack(">H", header[6:8])[0]
        payload = _extract_bytes_from_positions(
            bytes(pixels), positions, LSB_HEADER_SIZE + token_len, self.key
        )
        token = payload[LSB_HEADER_SIZE:]
        compressed = self.cipher.decrypt(token)
        return zlib.decompress(compressed).decode("utf-8")

    def _unpack_legacy_append(self, image_path: Path) -> str:
        data = image_path.read_bytes()
        marker_pos = data.find(MAGIC_MARKER)
        if marker_pos < 0:
            raise ValueError("Legacy marker not found")
        encrypted = data[marker_pos + len(MAGIC_MARKER) :]
        # Legacy payload had custom signature + compressed bytes inside Fernet token.
        blob = self.cipher.decrypt(encrypted)
        if len(blob) < 32:
            raise ValueError("Invalid legacy payload size")
        compressed = blob[32:]
        return zlib.decompress(compressed).decode("utf-8")

    def unpack(self, stego_image_path: Path) -> Optional[str]:
        """Extract and decrypt payload from stego image (LSB first, legacy fallback)."""
        try:
            return self._unpack_lsb_png(stego_image_path)
        except Exception as lsb_error:
            logger.debug("LSB unpack failed (%s), trying legacy mode", lsb_error)
            try:
                return self._unpack_legacy_append(stego_image_path)
            except Exception as legacy_error:
                logger.error(f"Stego unpack failed: {legacy_error}")
                return None

    def get_key_str(self) -> str:
        return self.key.decode("utf-8")


def generate_stego_assets(
    config_dir: Path, assets_dir: Path, secret_key: Optional[str] = None
) -> None:
    """
    Scan output directory for singbox.json and generate stego PNG variants.
    """
    config_file = config_dir / "singbox.json"
    if not config_file.exists():
        logger.warning(f"Config file not found: {config_file}")
        return

    if not secret_key:
        from configstream.config import AppSettings

        settings = AppSettings()
        secret_key = settings.STEGO_KEY or settings.CONFIG_STREAM_KEY

    if secret_key:
        try:
            key = secret_key.encode()
            Fernet(key)  # validate key shape
        except Exception as exc:
            # An invalid STEGO_KEY produces stego artifacts that can never be
            # decrypted by clients holding the correct key.  Silently falling
            # back to an ephemeral key would produce unverifiable output that
            # looks valid but is useless — fail loudly instead.
            raise ValueError(
                f"STEGO_KEY is set but is not a valid Fernet key: {exc}. "
                'Generate a valid key with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            ) from exc
    else:
        # No key at all — refuse to proceed so that the CI run fails
        # visibly rather than producing artifacts encrypted under a random key
        # that cannot be reproduced or verified by any client.
        raise ValueError(
            "STEGO_KEY / CONFIG_STREAM_KEY is not set. "
            "Steganography requires a stable key so that clients can decrypt the payload. "
            "Set the STEGO_KEY environment variable (or secret) before running this step."
        )

    packer = StegoPacker(key)
    content = config_file.read_text(encoding="utf-8")

    covers = list(assets_dir.glob("*.png"))
    if not covers:
        logger.warning("No cover images found for steganography.")
        return

    for cover in covers:
        output_name = f"stealth_{cover.name}"
        packer.pack(cover, content, config_dir / output_name)
