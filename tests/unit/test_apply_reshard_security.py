# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression coverage for the local reshard helper's subprocess contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "apply_reshard.py"
SPEC = importlib.util.spec_from_file_location("apply_reshard", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
apply_reshard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(apply_reshard)


def test_resolve_executable_returns_absolute_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(apply_reshard.shutil, "which", lambda name: f"/usr/bin/{name}")

    assert apply_reshard._resolve_executable("git") == "/usr/bin/git"


def test_resolve_executable_fails_closed_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(apply_reshard.shutil, "which", lambda _name: None)

    with pytest.raises(SystemExit, match="gh CLI not found on PATH"):
        apply_reshard._resolve_executable("gh")
