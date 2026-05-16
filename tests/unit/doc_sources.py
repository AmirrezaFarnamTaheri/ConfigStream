# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared helpers for documentation source regression tests."""

from __future__ import annotations

from pathlib import Path


def read_doc(repo_root: Path, rel_path: str) -> str:
    return (repo_root / rel_path).read_text(encoding="utf-8")


def read_first_existing_doc(repo_root: Path, rel_paths: list[str]) -> str:
    for rel_path in rel_paths:
        path = repo_root / rel_path
        if path.exists():
            return path.read_text(encoding="utf-8")

    expected = ", ".join(rel_paths)
    raise AssertionError(f"Expected at least one documentation source: {expected}")
