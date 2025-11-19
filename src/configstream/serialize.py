"""
Serialization helpers for deterministic and atomic JSON outputs.
"""

from __future__ import annotations

import json
import logging
import tempfile
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import orjson
except ImportError:
    orjson = None

def dumps(data: Any) -> str:
    """Fast JSON serialization."""
    if orjson:
        return orjson.dumps(
            data,
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS | orjson.OPT_NON_STR_KEYS
        ).decode("utf-8")

    return json.dumps(data, indent=2, sort_keys=True, default=str)

def dump_to_path(path: Path, data: Any) -> None:
    """Atomic write to file."""
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file in same directory to ensure atomic move works
        # (os.rename across filesystems fails)
        tmp_path = path.with_suffix(path.suffix + ".tmp")

        content = dumps(data)
        tmp_path.write_text(content, encoding="utf-8")

        # Atomic replacement
        tmp_path.replace(path)

    except Exception as e:
        logger.error(f"Failed to write {path}: {e}")
