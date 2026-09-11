# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
from typing import NoReturn

import pytest

from scripts import finalize_release_outputs


def _unexpected_read_text(*args: object, **kwargs: object) -> NoReturn:
    raise AssertionError("oversized release input must be rejected before read_text")


def test_load_rejects_oversized_release_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = tmp_path / "proxies.json"
    payload.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(finalize_release_outputs, "MAX_RELEASE_INPUT_BYTES", 1)
    monkeypatch.setattr(Path, "read_text", _unexpected_read_text)
    with pytest.raises(ValueError, match="size limit"):
        finalize_release_outputs._load(payload, [])


def test_cleanup_rejects_oversized_text_before_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = tmp_path / "huge.txt"
    payload.write_text("abcd", encoding="utf-8")
    monkeypatch.setattr(finalize_release_outputs, "MAX_RELEASE_INPUT_BYTES", 1)
    monkeypatch.setattr(Path, "read_text", _unexpected_read_text)
    with pytest.raises(ValueError, match="size limit"):
        finalize_release_outputs._cleanup(tmp_path)
