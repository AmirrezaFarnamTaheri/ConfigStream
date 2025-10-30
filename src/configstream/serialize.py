"""Serialization helpers for deterministic JSON outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional speed-up
    import orjson
except Exception:  # pragma: no cover - fallback to stdlib
    orjson = None  # type: ignore[assignment]


def dumps(data: Any) -> str:
    if orjson is not None:
        return orjson.dumps(
            data,
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        ).decode()
    return json.dumps(data, indent=2, sort_keys=True)


def dump_to_path(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(dumps(data), encoding="utf-8")
    tmp.replace(path)
