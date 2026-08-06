# SPDX-License-Identifier: AGPL-3.0-or-later
"""Backward-compatible lazy forwarders for producer helpers.

Keeping the imports inside the call sites prevents the pipeline package from
loading HTTP-client dependencies when callers only need orchestration or dry-run
behavior.
"""

from __future__ import annotations

from typing import Any


async def fetch_multiple_sources(*args: Any, **kwargs: Any):
    from configstream.pipeline.fetcher import fetch_multiple_sources as _fetch

    return await _fetch(*args, **kwargs)


async def read_multiple_files_async(*args: Any, **kwargs: Any):
    from configstream.async_file_ops import read_multiple_files_async as _read

    return await _read(*args, **kwargs)


__all__ = ["fetch_multiple_sources", "read_multiple_files_async"]
