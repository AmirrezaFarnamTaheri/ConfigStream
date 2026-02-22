# SPDX-License-Identifier: AGPL-3.0-or-later
"""Guardrail: no blocking requests usage in async core modules."""

from __future__ import annotations

from pathlib import Path


def test_no_requests_imports_in_async_core() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "configstream"
    offenders: list[str] = []
    for py_file in root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("import requests") or stripped.startswith(
                "from requests"
            ):
                offenders.append(str(py_file.relative_to(root)))
                break
    assert not offenders, f"Blocking requests imports found: {offenders}"
