# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprehensive tests for steganography transport module."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from configstream.stego import MAGIC_MARKER, StegoPacker, generate_stego_assets


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    import binascii

    crc = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def _make_valid_png(
    path: Path, width: int = 32, height: int = 32, rgba: bool = True
) -> None:
    sig = b"\x89PNG\r\n\x1a\n"
    color_type = 6 if rgba else 2
    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)

    rows = bytearray()
    for y in range(height):
        rows.append(0)  # filter None
        for x in range(width):
            r = (x * 11 + y * 7) & 0xFF
            g = (x * 5 + y * 13) & 0xFF
            b = (x * 3 + y * 17) & 0xFF
            rows.extend((r, g, b))
            if rgba:
                rows.append(255)
    idat = zlib.compress(bytes(rows), level=9)

    data = bytearray(sig)
    data.extend(_png_chunk(b"IHDR", ihdr))
    data.extend(_png_chunk(b"IDAT", idat))
    data.extend(_png_chunk(b"IEND", b""))
    path.write_bytes(bytes(data))


class TestStegoPacker:
    def test_init_with_key(self) -> None:
        key = Fernet.generate_key()
        packer = StegoPacker(key=key)
        assert packer.key == key
        assert packer.cipher is not None

    def test_init_without_key(self) -> None:
        packer = StegoPacker()
        assert packer.key is not None
        assert len(packer.key) > 0
        assert packer.cipher is not None

    def test_get_key_str(self) -> None:
        key = Fernet.generate_key()
        packer = StegoPacker(key=key)
        assert packer.get_key_str() == key.decode("utf-8")

    def test_pack_success(self, tmp_path: Path) -> None:
        cover = tmp_path / "cover.png"
        out = tmp_path / "out.png"
        _make_valid_png(cover)
        packer = StegoPacker()
        assert packer.pack(cover, "test configuration data", out) is True
        assert out.exists()
        assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    def test_pack_and_unpack_roundtrip(self, tmp_path: Path) -> None:
        cover = tmp_path / "cover.png"
        out = tmp_path / "out.png"
        _make_valid_png(cover)
        packer = StegoPacker()
        payload = '{"outbounds":[{"type":"vless","tag":"node"}]}'
        assert packer.pack(cover, payload, out) is True
        decoded = packer.unpack(out)
        assert decoded == payload

    def test_pack_cover_image_not_found(self, tmp_path: Path) -> None:
        cover = tmp_path / "missing.png"
        out = tmp_path / "out.png"
        packer = StegoPacker()
        assert packer.pack(cover, "test", out) is False
        assert not out.exists()

    def test_pack_invalid_cover_png(self, tmp_path: Path) -> None:
        cover = tmp_path / "cover.png"
        out = tmp_path / "out.png"
        cover.write_bytes(b"NOT_A_PNG")
        packer = StegoPacker()
        assert packer.pack(cover, "test", out) is False

    def test_pack_capacity_failure(self, tmp_path: Path) -> None:
        cover = tmp_path / "tiny.png"
        out = tmp_path / "out.png"
        _make_valid_png(cover, width=8, height=8)
        packer = StegoPacker()
        # Intentionally too large for tiny image capacity.
        huge_payload = "X" * 50_000
        assert packer.pack(cover, huge_payload, out) is False

    def test_unpack_legacy_append_fallback(self, tmp_path: Path) -> None:
        key = Fernet.generate_key()
        packer = StegoPacker(key=key)
        legacy = tmp_path / "legacy.bin"

        payload = "legacy payload"
        compressed = zlib.compress(payload.encode("utf-8"), level=9)
        signature = b"\x00" * 32
        encrypted = packer.cipher.encrypt(signature + compressed)
        legacy.write_bytes(b"IMG" + MAGIC_MARKER + encrypted)

        assert packer.unpack(legacy) == payload

    def test_unpack_wrong_key(self, tmp_path: Path) -> None:
        cover = tmp_path / "cover.png"
        out = tmp_path / "out.png"
        _make_valid_png(cover)
        p1 = StegoPacker()
        p2 = StegoPacker()
        assert p1.pack(cover, "secret data", out) is True
        assert p2.unpack(out) is None


class TestGenerateStegoAssets:
    def test_generate_with_existing_config(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "configs"
        assets_dir = tmp_path / "assets"
        config_dir.mkdir()
        assets_dir.mkdir()

        (config_dir / "singbox.json").write_text('{"outbounds":[]}', encoding="utf-8")
        _make_valid_png(assets_dir / "cover1.png")
        _make_valid_png(assets_dir / "cover2.png", rgba=False)

        generate_stego_assets(config_dir, assets_dir)
        assert (config_dir / "stealth_cover1.png").exists()
        assert (config_dir / "stealth_cover2.png").exists()

    def test_generate_with_secret_key(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "configs"
        assets_dir = tmp_path / "assets"
        config_dir.mkdir()
        assets_dir.mkdir()

        (config_dir / "singbox.json").write_text('{"test":"data"}', encoding="utf-8")
        _make_valid_png(assets_dir / "cover.png")
        key = Fernet.generate_key().decode("utf-8")

        generate_stego_assets(config_dir, assets_dir, key)
        assert (config_dir / "stealth_cover.png").exists()

    def test_generate_without_config_file(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        config_dir = tmp_path / "configs"
        assets_dir = tmp_path / "assets"
        config_dir.mkdir()
        assets_dir.mkdir()
        generate_stego_assets(config_dir, assets_dir)
        assert any("not found" in r.message.lower() for r in caplog.records)

    def test_generate_without_cover_images(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        config_dir = tmp_path / "configs"
        assets_dir = tmp_path / "assets"
        config_dir.mkdir()
        assets_dir.mkdir()
        (config_dir / "singbox.json").write_text('{"test":"data"}', encoding="utf-8")
        generate_stego_assets(config_dir, assets_dir)
        assert any("no cover images" in r.message.lower() for r in caplog.records)


class TestMagicMarker:
    def test_magic_marker_constant(self) -> None:
        assert MAGIC_MARKER == b"CSTREAM_PAYLOAD_START>>"
        assert isinstance(MAGIC_MARKER, bytes)


class TestStegoKeyDerivationKAT:
    def test_derive_offsets_known_answer_vector_coprime(self) -> None:
        from configstream.stego import _derive_offsets
        key = b"dummy_key_material_for_stego_kat"
        start, stride = _derive_offsets(key, 1000)
        assert start == 246
        assert stride == 463

    def test_derive_offsets_known_answer_vector_with_conflict_resolution(self) -> None:
        from configstream.stego import _derive_offsets
        key = b"key_1"
        start, stride = _derive_offsets(key, 1000)
        assert start == 316
        assert stride == 187

