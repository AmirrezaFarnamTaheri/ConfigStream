# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

import pytest

from scripts import finalize_release


def test_required_json_rejected_before_parse_when_oversized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = tmp_path / "proxies.json"
    payload.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(finalize_release, "MAX_REQUIRED_JSON_BYTES", 1)
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("oversized JSON must be rejected before read_text")
        ),
    )
    with pytest.raises(SystemExit, match="exceeds"):
        finalize_release._load_json(payload)
