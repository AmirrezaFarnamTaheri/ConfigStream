# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared JSON and string validation utilities for repository scripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_object(path: Path, root_label: str = "") -> dict[str, Any]:
    label = f"{root_label} " if root_label else ""
    if not path.is_file():
        raise FileNotFoundError(f"{label}JSON file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"Expected {label}JSON object in {path}, got {type(data).__name__}")
    return data


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
