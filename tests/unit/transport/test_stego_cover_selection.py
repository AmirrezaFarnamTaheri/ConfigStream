# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import binascii
import logging
import struct
import zlib
from pathlib import Path

from cryptography.fernet import Fernet

from configstream.stego import generate_stego_assets


def _chunk(kind: bytes, data: bytes) -> bytes:
    crc = binascii.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)


def _write_png(path: Path, size: int) -> None:
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            rows.extend(((x * 7) & 0xFF, (y * 11) & 0xFF, ((x + y) * 3) & 0xFF, 255))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + _chunk(b"IEND", b"")
    )


def test_generate_stego_assets_skips_tiny_cover(tmp_path: Path, caplog) -> None:
    config_dir = tmp_path / "output"
    assets_dir = tmp_path / "assets"
    config_dir.mkdir()
    assets_dir.mkdir()
    (config_dir / "singbox.json").write_text(
        '{"outbounds":[{"type":"direct","tag":"direct"}]}',
        encoding="utf-8",
    )
    _write_png(assets_dir / "favicon-16x16.png", 16)
    _write_png(assets_dir / "icon-128x128.png", 128)

    with caplog.at_level(logging.WARNING):
        generate_stego_assets(
            config_dir,
            assets_dir,
            Fernet.generate_key().decode("ascii"),
        )

    assert not (config_dir / "stealth_favicon-16x16.png").exists()
    assert (config_dir / "stealth_icon-128x128.png").exists()
    assert "favicon-16x16.png" in caplog.text


def test_generate_stego_assets_all_unsuitable_is_nonfatal(tmp_path: Path, caplog) -> None:
    config_dir = tmp_path / "output"
    assets_dir = tmp_path / "assets"
    config_dir.mkdir()
    assets_dir.mkdir()
    (config_dir / "singbox.json").write_text('{"outbounds":[]}', encoding="utf-8")
    _write_png(assets_dir / "favicon-16x16.png", 16)

    with caplog.at_level(logging.WARNING):
        generate_stego_assets(
            config_dir,
            assets_dir,
            Fernet.generate_key().decode("ascii"),
        )

    assert "No stego assets were generated" in caplog.text
