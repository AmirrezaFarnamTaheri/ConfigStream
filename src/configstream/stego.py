# SPDX-License-Identifier: AGPL-3.0-or-later
"""PNG LSB steganography transport with Fernet-authenticated payloads."""

from __future__ import annotations

import binascii
import hashlib
import logging
import math
import os
import struct
import zlib
from pathlib import Path
from typing import List, Optional

from cryptography.fernet import Fernet, InvalidToken

from .utils import AtomicFileWriter

logger = logging.getLogger(__name__)

MAGIC_MARKER = b"CSTREAM_PAYLOAD_START>>"
LSB_MAGIC = b"CSP2"
LEGACY_LSB_VERSION = 1
LSB_VERSION = 2
LEGACY_HEADER_SIZE = 8
SALT_SIZE = 16
LSB_HEADER_SIZE = 4 + 1 + 1 + 2 + SALT_SIZE
MAX_PIXELS = 100_000_000
MAX_TOKEN_BYTES = 0xFFFF
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
    estimate = a + b - c
    pa = abs(estimate - a)
    pb = abs(estimate - b)
    pc = abs(estimate - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _safe_decompress(data: bytes, expected: int) -> bytes:
    if expected <= 0 or expected > (MAX_PIXELS * 5):
        raise ValueError("Invalid PNG decompression size")
    decompressor = zlib.decompressobj()
    raw = decompressor.decompress(data, expected + 1)
    if (
        len(raw) != expected
        or not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
    ):
        raise ValueError("Invalid or oversized PNG scanline data")
    return raw


def _unfilter_png(raw: bytes, width: int, height: int, bpp: int) -> bytearray:
    row_size = width * bpp
    expected = (row_size + 1) * height
    if len(raw) != expected:
        raise ValueError("Invalid PNG scanline buffer size")

    output = bytearray(height * row_size)
    previous = bytearray(row_size)
    for y in range(height):
        source_start = y * (row_size + 1)
        filter_type = raw[source_start]
        source = raw[source_start + 1 : source_start + 1 + row_size]
        row = bytearray(row_size)
        for index, byte in enumerate(source):
            left = row[index - bpp] if index >= bpp else 0
            up = previous[index]
            up_left = previous[index - bpp] if index >= bpp else 0
            if filter_type == 0:
                value = byte
            elif filter_type == 1:
                value = byte + left
            elif filter_type == 2:
                value = byte + up
            elif filter_type == 3:
                value = byte + ((left + up) // 2)
            elif filter_type == 4:
                value = byte + _paeth_predictor(left, up, up_left)
            else:
                raise ValueError(f"Unsupported PNG filter type: {filter_type}")
            row[index] = value & 0xFF
        output[y * row_size : (y + 1) * row_size] = row
        previous = row
    return output


def _filter_none(raw_pixels: bytes, width: int, height: int, bpp: int) -> bytes:
    row_size = width * bpp
    output = bytearray((row_size + 1) * height)
    for y in range(height):
        destination = y * (row_size + 1)
        source = y * row_size
        output[destination] = 0
        output[destination + 1 : destination + 1 + row_size] = raw_pixels[
            source : source + row_size
        ]
    return bytes(output)


def _derive_offsets(
    key_material: bytes,
    carrier_len: int,
    salt: bytes = b"",
) -> tuple[int, int]:
    if carrier_len <= 0:
        raise ValueError("carrier_len must be positive")
    if salt:
        if len(salt) != SALT_SIZE:
            raise ValueError("Invalid LSB salt length")
        derivation_input = (
            b"ConfigStream-LSB-v2\0"
            + key_material
            + salt
            + struct.pack(">Q", carrier_len)
        )
    else:
        # Legacy v1 path: no domain prefix — preserved for backward compatibility
        # with existing v1 carriers. New carriers use derive_lsb_offsets (HMAC).
        derivation_input = key_material + struct.pack(">Q", carrier_len)
    digest = hashlib.sha256(derivation_input).digest()
    start = int.from_bytes(digest[:8], "big") % carrier_len
    stride = max(1, (int.from_bytes(digest[8:16], "big") % carrier_len) | 1)
    while math.gcd(stride, carrier_len) != 1:
        stride = (stride + 2) % carrier_len or 1
    return start, stride


def _read_png(
    png_bytes: bytes,
) -> tuple[int, int, int, list[tuple[bytes, bytes]], bytes]:
    if not png_bytes.startswith(_PNG_SIG):
        raise ValueError("Not a PNG file")

    position = len(_PNG_SIG)
    chunks: list[tuple[bytes, bytes]] = []
    idat_parts: list[bytes] = []
    width = height = bpp = 0
    saw_ihdr = False
    saw_iend = False

    while position + 12 <= len(png_bytes):
        length = struct.unpack(">I", png_bytes[position : position + 4])[0]
        chunk_type = png_bytes[position + 4 : position + 8]
        data_start = position + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end > len(png_bytes):
            raise ValueError("Truncated PNG chunk")
        chunk_data = png_bytes[data_start:data_end]
        stored_crc = struct.unpack(">I", png_bytes[data_end:crc_end])[0]
        if stored_crc != _crc32(chunk_type, chunk_data):
            raise ValueError("PNG chunk CRC mismatch")
        chunks.append((chunk_type, chunk_data))

        if chunk_type == b"IHDR":
            if saw_ihdr or length != 13:
                raise ValueError("Invalid PNG IHDR")
            saw_ihdr = True
            width, height, bit_depth, color_type, compression, filt, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
                raise ValueError("PNG dimensions exceed safety limit")
            if bit_depth != 8 or compression != 0 or filt != 0 or interlace != 0:
                raise ValueError("Unsupported PNG format for stego packing")
            if color_type == 2:
                bpp = 3
            elif color_type == 6:
                bpp = 4
            else:
                raise ValueError("Only RGB and RGBA PNG files are supported")
        elif chunk_type == b"IDAT":
            if not saw_ihdr:
                raise ValueError("IDAT appeared before IHDR")
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            saw_iend = True
            position = crc_end
            break
        position = crc_end

    if not saw_ihdr or not saw_iend or not idat_parts or bpp == 0:
        raise ValueError("Invalid PNG structure")
    if position != len(png_bytes):
        raise ValueError("Unexpected bytes after PNG IEND")
    return width, height, bpp, chunks, b"".join(idat_parts)


def _build_carrier_positions(width: int, height: int, bpp: int) -> list[int]:
    row_size = width * bpp
    positions: list[int] = []
    for y in range(height):
        row_base = y * row_size
        for x in range(width):
            pixel = row_base + (x * bpp)
            positions.extend((pixel, pixel + 1, pixel + 2))
    return positions


def _sequential_embed(
    raw_pixels: bytearray,
    positions: list[int],
    payload: bytes,
) -> None:
    needed = len(payload) * 8
    if needed > len(positions):
        raise ValueError("Payload exceeds carrier capacity")
    for bit_index in range(needed):
        bit = (payload[bit_index // 8] >> (7 - (bit_index % 8))) & 1
        raw_index = positions[bit_index]
        raw_pixels[raw_index] = (raw_pixels[raw_index] & 0xFE) | bit


def _sequential_extract(raw_pixels: bytes, positions: list[int], length: int) -> bytes:
    needed = length * 8
    if needed > len(positions):
        raise ValueError("Requested data exceeds carrier capacity")
    output = bytearray(length)
    for bit_index in range(needed):
        bit = raw_pixels[positions[bit_index]] & 1
        output[bit_index // 8] = (output[bit_index // 8] << 1) | bit
    return bytes(output)


def _embed_permuted(
    raw_pixels: bytearray,
    positions: list[int],
    payload: bytes,
    key_material: bytes,
    salt: bytes,
    stego_version: int = 2,
) -> None:
    needed = len(payload) * 8
    if needed > len(positions):
        raise ValueError("Payload exceeds carrier capacity")
    if stego_version >= 2:
        offsets = derive_lsb_offsets(key_material + salt, len(positions), needed)
        for bit_index in range(needed):
            bit = (payload[bit_index // 8] >> (7 - (bit_index % 8))) & 1
            raw_index = positions[offsets[bit_index]]
            raw_pixels[raw_index] = (raw_pixels[raw_index] & 0xFE) | bit
    else:
        start, stride = _derive_offsets(key_material, len(positions), salt)
        for bit_index in range(needed):
            bit = (payload[bit_index // 8] >> (7 - (bit_index % 8))) & 1
            position_index = (start + bit_index * stride) % len(positions)
            raw_index = positions[position_index]
            raw_pixels[raw_index] = (raw_pixels[raw_index] & 0xFE) | bit


def _extract_permuted(
    raw_pixels: bytes,
    positions: list[int],
    length: int,
    key_material: bytes,
    salt: bytes,
    stego_version: int = 2,
) -> bytes:
    needed = length * 8
    if needed > len(positions):
        raise ValueError("Requested data exceeds carrier capacity")
    output = bytearray(length)
    if stego_version >= 2:
        offsets = derive_lsb_offsets(key_material + salt, len(positions), needed)
        for bit_index in range(needed):
            bit = raw_pixels[positions[offsets[bit_index]]] & 1
            output[bit_index // 8] = (output[bit_index // 8] << 1) | bit
    else:
        start, stride = _derive_offsets(key_material, len(positions), salt)
        for bit_index in range(needed):
            position_index = (start + bit_index * stride) % len(positions)
            bit = raw_pixels[positions[position_index]] & 1
            output[bit_index // 8] = (output[bit_index // 8] << 1) | bit
    return bytes(output)


def _replace_idat(chunks: list[tuple[bytes, bytes]], new_idat: bytes) -> bytes:
    output = bytearray(_PNG_SIG)
    idat_written = False
    for chunk_type, chunk_data in chunks:
        if chunk_type == b"IDAT":
            if not idat_written:
                output.extend(_pack_chunk(b"IDAT", new_idat))
                idat_written = True
            continue
        output.extend(_pack_chunk(chunk_type, chunk_data))
    if not idat_written:
        raise ValueError("PNG did not contain IDAT")
    return bytes(output)


class StegoPacker:
    def __init__(self, key: Optional[bytes] = None):
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def _encrypt(self, payload_data: str) -> bytes:
        token = self.cipher.encrypt(zlib.compress(payload_data.encode("utf-8"), level=9))
        if not token or len(token) > MAX_TOKEN_BYTES:
            raise ValueError("Stego token exceeds header size limit")
        return token

    def _pack_lsb_png(self, cover_image_path: Path, token: bytes) -> bytes:
        png_bytes = cover_image_path.read_bytes()
        width, height, bpp, chunks, idat_data = _read_png(png_bytes)
        expected = (width * bpp + 1) * height
        pixels = _unfilter_png(_safe_decompress(idat_data, expected), width, height, bpp)
        positions = _build_carrier_positions(width, height, bpp)

        salt = os.urandom(SALT_SIZE)
        header = (
            LSB_MAGIC
            + bytes([LSB_VERSION, 0])
            + struct.pack(">H", len(token))
            + salt
        )
        bootstrap_bits = len(header) * 8
        if bootstrap_bits >= len(positions):
            raise ValueError("Cover image is too small for the stego header")
        bootstrap_positions = positions[:bootstrap_bits]
        payload_positions = positions[bootstrap_bits:]
        _sequential_embed(pixels, bootstrap_positions, header)
        _embed_permuted(pixels, payload_positions, token, self.key, salt, stego_version=LSB_VERSION)

        filtered = _filter_none(bytes(pixels), width, height, bpp)
        return _replace_idat(chunks, zlib.compress(filtered, level=9))

    def pack(self, cover_image_path: Path, payload_data: str, output_path: Path) -> bool:
        try:
            if not cover_image_path.is_file():
                logger.error("Cover image not found")
                return False
            final_bytes = self._pack_lsb_png(cover_image_path, self._encrypt(payload_data))
            AtomicFileWriter.write_bytes(output_path, final_bytes)
            logger.info("Stego image created (%d bytes, salted LSB mode)", len(final_bytes))
            return True
        except (OSError, ValueError, zlib.error) as exc:
            logger.error(
                "Stego packing failed for %s: %s",
                cover_image_path.name,
                type(exc).__name__,
            )
            return False

    def _unpack_lsb_png(self, image_path: Path) -> str:
        png_bytes = image_path.read_bytes()
        width, height, bpp, _chunks, idat_data = _read_png(png_bytes)
        expected = (width * bpp + 1) * height
        pixels = _unfilter_png(_safe_decompress(idat_data, expected), width, height, bpp)
        positions = _build_carrier_positions(width, height, bpp)

        prefix = _sequential_extract(bytes(pixels), positions, LEGACY_HEADER_SIZE)
        if prefix[:4] == LSB_MAGIC and prefix[4] == LSB_VERSION:
            header = _sequential_extract(bytes(pixels), positions, LSB_HEADER_SIZE)
            token_length = struct.unpack(">H", header[6:8])[0]
            if token_length <= 0:
                raise ValueError("Invalid LSB token length")
            salt = header[8 : 8 + SALT_SIZE]
            bootstrap_bits = LSB_HEADER_SIZE * 8
            token = _extract_permuted(
                bytes(pixels),
                positions[bootstrap_bits:],
                token_length,
                self.key,
                salt,
                stego_version=LSB_VERSION,
            )
        else:
            legacy_header = _extract_permuted(
                bytes(pixels), positions, LEGACY_HEADER_SIZE, self.key, b"", stego_version=1
            )
            if legacy_header[:4] != LSB_MAGIC or legacy_header[4] != LEGACY_LSB_VERSION:
                raise ValueError("LSB stego marker not found")
            token_length = struct.unpack(">H", legacy_header[6:8])[0]
            if token_length <= 0:
                raise ValueError("Invalid legacy LSB token length")
            legacy_payload = _extract_permuted(
                bytes(pixels),
                positions,
                LEGACY_HEADER_SIZE + token_length,
                self.key,
                b"",
                stego_version=1,
            )
            token = legacy_payload[LEGACY_HEADER_SIZE:]

        compressed = self.cipher.decrypt(token)
        return zlib.decompress(compressed).decode("utf-8")

    def _unpack_legacy_append(self, image_path: Path) -> str:
        data = image_path.read_bytes()
        marker_position = data.rfind(MAGIC_MARKER)
        if marker_position < 0:
            raise ValueError("Legacy marker not found")
        encrypted = data[marker_position + len(MAGIC_MARKER) :]
        blob = self.cipher.decrypt(encrypted)
        if len(blob) < 32:
            raise ValueError("Invalid legacy payload size")
        return zlib.decompress(blob[32:]).decode("utf-8")

    def unpack(self, stego_image_path: Path) -> Optional[str]:
        expected_errors = (OSError, ValueError, zlib.error, InvalidToken, UnicodeDecodeError)
        try:
            return self._unpack_lsb_png(stego_image_path)
        except expected_errors as lsb_error:
            logger.debug("LSB unpack failed (%s); trying legacy mode", type(lsb_error).__name__)
            try:
                return self._unpack_legacy_append(stego_image_path)
            except expected_errors as legacy_error:
                logger.error("Stego unpack failed: %s", type(legacy_error).__name__)
                return None

    def get_key_str(self) -> str:
        return self.key.decode("utf-8")


def generate_stego_assets(
    config_dir: Path,
    assets_dir: Path,
    secret_key: Optional[str] = None,
) -> None:
    config_file = config_dir / "singbox.json"
    if not config_file.is_file():
        logger.warning("Config file for steganography was not found")
        return

    if not secret_key:
        from configstream.config import AppSettings

        settings = AppSettings()
        secret_key = settings.STEGO_KEY or settings.CONFIG_STREAM_KEY
    if not secret_key:
        raise ValueError("STEGO_KEY / CONFIG_STREAM_KEY is required")

    try:
        key = secret_key.encode("ascii")
        Fernet(key)
    except (UnicodeEncodeError, ValueError) as exc:
        raise ValueError("STEGO_KEY is not a valid Fernet key") from exc

    packer = StegoPacker(key)
    content = config_file.read_text(encoding="utf-8")
    covers = sorted(assets_dir.glob("*.png"))
    if not covers:
        logger.warning("No cover images found for steganography")
        return

    generated = 0
    skipped: list[str] = []
    for cover in covers:
        output_path = config_dir / f"stealth_{cover.name}"
        if packer.pack(cover, content, output_path):
            generated += 1
        else:
            skipped.append(cover.name)

    if skipped:
        logger.warning(
            "Skipped %d unsuitable stego cover(s): %s",
            len(skipped),
            ", ".join(skipped),
        )
    if generated == 0:
        logger.warning("No stego assets were generated from %d cover image(s)", len(covers))


def derive_lsb_offsets(key: bytes, max_index: int, count: int) -> List[int]:
    """Derive deterministic, pseudorandom LSB pixel indices using HMAC-SHA256."""
    if max_index <= 0 or count <= 0:
        raise ValueError("max_index and count must be positive")
    if count > max_index:
        raise ValueError(f"count ({count}) cannot exceed max_index ({max_index})")

    offsets: list[int] = []
    counter = 0
    import hmac
    while len(offsets) < count:
        msg = struct.pack(">I", counter)
        h = hmac.new(key, msg, hashlib.sha256).digest()
        for i in range(0, len(h), 4):
            val = struct.unpack(">I", h[i:i+4])[0]
            idx = val % max_index
            if idx not in offsets:
                offsets.append(idx)
                if len(offsets) == count:
                    break
        counter += 1
    return offsets
