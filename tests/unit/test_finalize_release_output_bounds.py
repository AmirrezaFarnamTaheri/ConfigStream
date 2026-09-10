# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

import pytest

from scripts import finalize_release_outputs


def test_load_rejects_oversized_release_input(tmp_path: Path, monkeypatch) -> None:
    payload = tmp_path / "proxies.json"
    payload.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(finalize_release_outputs, "MAX_RELEASE_INPUT_BYTES", 1)
    with pytest.raises(ValueError, match="size limit"):
        finalize_release_outputs._load(payload, [])


def test_cleanup_rejects_oversized_text_before_read(
    tmp_path: Path, monkeypatch
) -> None:
    payload = tmp_path / "huge.txt"
    payload.write_text("abcd", encoding="utf-8")
    monkeypatch.setattr(finalize_release_outputs, "MAX_RELEASE_INPUT_BYTES", 1)
    with pytest.raises(ValueError, match="size limit"):
        finalize_release_outputs._cleanup(tmp_path)
