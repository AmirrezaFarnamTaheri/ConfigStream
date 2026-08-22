# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import struct
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from configstream.event_stream import EventStream
from configstream.intelligence.washer.key_generator import KeyGenerator
from configstream.intelligence.washer.utils import make_entry
from configstream.server import ws
from configstream.stego import StegoPacker, _derive_offsets


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    crc = binascii.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)


def _make_rgb_png(path: Path, width: int = 96, height: int = 96) -> None:
    rows = b"".join(b"\x00" + (b"\x7f\x80\x81" * width) for _ in range(height))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(rows))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def test_key_generator_parses_ipv6_and_rejects_bad_ports() -> None:
    assert KeyGenerator._parse_endpoint("[2606:4700::1111]:2408") == (
        "2606:4700::1111",
        2408,
    )
    assert KeyGenerator._parse_endpoint("2606:4700::1111") == (
        "2606:4700::1111",
        2408,
    )
    assert KeyGenerator._parse_endpoint("example.com:65535") == (
        "example.com",
        65535,
    )
    assert KeyGenerator._parse_endpoint("example.com:70000") == (
        KeyGenerator.DEFAULT_ENDPOINT,
        KeyGenerator.DEFAULT_PORT,
    )


def test_scraped_warp_entries_are_unverified() -> None:
    private_key = base64.b64encode(bytes(range(32))).decode("ascii")
    proxy = make_entry(
        "test",
        private_key,
        "162.159.192.1",
        None,
        [0, 0, 0],
        2408,
    )
    assert proxy is not None
    assert proxy.is_working is False
    assert proxy.details["candidate_id"].startswith("WARP-test-")
    assert proxy.details["reserved"] == [0, 0, 0]


def test_websocket_wildcard_never_allows_arbitrary_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wildcard_settings = SimpleNamespace(ALLOWED_ORIGINS="*", ALLOWED_ORIGIN_REGEX="")
    monkeypatch.setattr(ws, "settings", wildcard_settings)
    assert ws._is_allowed_origin("https://attacker.example") is False

    explicit_settings = SimpleNamespace(
        ALLOWED_ORIGINS="https://app.example",
        ALLOWED_ORIGIN_REGEX="",
    )
    monkeypatch.setattr(ws, "settings", explicit_settings)
    assert ws._is_allowed_origin("https://app.example") is True
    assert ws._is_allowed_origin("https://attacker.example") is False


@pytest.mark.asyncio
async def test_event_stream_flushes_all_records_on_close(tmp_path: Path) -> None:
    stream = EventStream(tmp_path)
    for index in range(300):
        stream.emit("test", f"event-{index}")
    await stream.aclose()

    records = [
        json.loads(line)
        for line in (tmp_path / "pipeline_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(records) == 301
    assert records[0]["message"] == "event-0"
    assert records[-1]["event_type"] == "stream_close"


def test_legacy_stego_offset_derivation_is_preserved() -> None:
    key = b"legacy-key-material"
    carrier_len = 997
    digest = hashlib.sha256(key + struct.pack(">Q", carrier_len)).digest()
    expected_start = int.from_bytes(digest[:8], "big") % carrier_len
    expected_stride = max(
        1,
        (int.from_bytes(digest[8:16], "big") % carrier_len) | 1,
    )
    while math.gcd(expected_stride, carrier_len) != 1:
        expected_stride = (expected_stride + 2) % carrier_len or 1

    assert _derive_offsets(key, carrier_len) == (expected_start, expected_stride)
    assert _derive_offsets(key, carrier_len, b"x" * 16) != (
        expected_start,
        expected_stride,
    )


def test_stego_round_trip_uses_per_image_salt(tmp_path: Path) -> None:
    cover = tmp_path / "cover.png"
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    _make_rgb_png(cover)

    key = b"MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    packer = StegoPacker(key)
    payload = '{"outbounds": [{"type": "direct"}]}'

    assert packer.pack(cover, payload, first)
    assert packer.pack(cover, payload, second)
    assert first.read_bytes() != second.read_bytes()
    assert packer.unpack(first) == payload
    assert packer.unpack(second) == payload


def test_direct_go_tester_manager_import_uses_verified_launcher() -> None:
    from configstream.testers.go_tester.manager import GoBatchTester as direct
    from configstream.testers.go_tester.secure_manager import GoBatchTester as verified

    assert direct is verified
