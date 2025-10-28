"""Simple persistent cache for ETag/Last-Modified headers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Mapping

from .async_file_ops import ensure_directory

ETAG_CACHE_PATH = Path("output/.etag-cache.json")


def load_etags() -> Dict[str, Dict[str, str]]:
    """Load cached validator headers from disk."""

    if not ETAG_CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(ETAG_CACHE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): dict(v) for k, v in data.items() if isinstance(v, Mapping)}
    except json.JSONDecodeError:
        return {}
    return {}


def save_etags(values: Mapping[str, Mapping[str, str]]) -> None:
    """Persist validator headers to disk."""

    ensure_directory(ETAG_CACHE_PATH.parent)
    serialisable = {
        url: valid_headers
        for url, headers in values.items()
        if (valid_headers := {k: v for k, v in headers.items() if v})
    }
    ETAG_CACHE_PATH.write_text(json.dumps(serialisable, indent=2, sort_keys=True), encoding="utf-8")
