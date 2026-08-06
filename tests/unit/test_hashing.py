# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from configstream.hashing import sha256_file, sha256_json


def test_sha256_file_streams_exact_file_bytes(tmp_path: Path) -> None:
    payload = (b"configstream\x00" * 100_000) + b"tail"
    target = tmp_path / "artifact.bin"
    target.write_bytes(payload)

    assert sha256_file(target) == hashlib.sha256(payload).hexdigest()


def test_sha256_json_uses_stable_canonical_encoding() -> None:
    left = {"z": [3, 2, 1], "a": {"unicode": "سلام"}}
    right = {"a": {"unicode": "سلام"}, "z": [3, 2, 1]}
    canonical = json.dumps(
        left,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    assert sha256_json(left) == sha256_json(right)
    assert sha256_json(left) == hashlib.sha256(canonical).hexdigest()
