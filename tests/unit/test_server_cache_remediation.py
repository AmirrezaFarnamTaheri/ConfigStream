# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for server _read_json_file_async cache stampede prevention.

Task 2 of the Post-Audit Remediation Plan.
Verifies that concurrent async calls for the same uncached path result in
exactly ONE actual disk read (via asyncio.Lock double-checked locking).
"""

import asyncio
import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, MagicMock

from configstream.server.utils import _read_json_file_async, _json_cache, _cache_locks
from configstream.server.utils import _read_json_file


def test_json_read_retries_transient_sharing_failure(tmp_path: Path) -> None:
    with (
        patch.object(
            Path, "read_text", side_effect=[PermissionError(), '{"ok": true}']
        ),
        patch("configstream.server.utils.time.sleep") as sleep,
    ):
        assert _read_json_file(tmp_path / "state.json") == {"ok": True}
    sleep.assert_called_once_with(0.01)


def test_json_read_permission_retries_are_bounded(tmp_path: Path) -> None:
    with (
        patch.object(Path, "read_text", side_effect=PermissionError()) as read,
        patch("configstream.server.utils.time.sleep") as sleep,
    ):
        with pytest.raises(PermissionError):
            _read_json_file(tmp_path / "state.json")
    assert read.call_count == 5
    assert sleep.call_count == 4


# ---------------------------------------------------------------------------
# Test 1: Cache stampede prevention — single disk read under concurrency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_stampede_single_read_execution(tmp_path: Path) -> None:
    """10 concurrent callers on a cache-miss path must trigger only 1 disk read."""
    json_file = tmp_path / "test_data.json"
    json_file.write_text('{"status": "ok"}')

    # Ensure this path is evicted from the module-level caches
    _json_cache.pop(json_file, None)
    _cache_locks.pop(json_file, None)

    read_count = 0
    fixed_mtime = json_file.stat().st_mtime

    def mock_read_sync(p: Path) -> Dict[str, Any]:
        """Synchronous read counter that simulates slow disk I/O."""
        nonlocal read_count
        read_count += 1
        return {"status": "ok"}

    # Patch the synchronous helper so we can count calls.
    # Also patch os.path.getmtime to return a stable value.
    with (
        patch(
            "configstream.server.utils._read_json_file",
            side_effect=mock_read_sync,
        ),
        patch(
            "configstream.server.utils.os.path.getmtime",
            return_value=fixed_mtime,
        ),
    ):
        # Fire 10 concurrent requests for the same file
        results = await asyncio.gather(
            *[_read_json_file_async(json_file) for _ in range(10)]
        )

    assert len(results) == 10
    assert all(r == {"status": "ok"} for r in results)
    # With stampede protection, only 1 actual disk read should occur
    assert read_count == 1, (
        f"Expected 1 disk read but got {read_count}. "
        "Cache stampede prevention (asyncio.Lock) is missing or broken."
    )


# ---------------------------------------------------------------------------
# Test 2: Cached result is returned without re-reading on subsequent calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_hit_skips_disk_read(tmp_path: Path) -> None:
    """A subsequent call for the same unchanged file must use the cache."""
    json_file = tmp_path / "cached_data.json"
    json_file.write_text('{"value": 42}')

    _json_cache.pop(json_file, None)
    _cache_locks.pop(json_file, None)

    read_count = 0
    fixed_mtime = json_file.stat().st_mtime

    def mock_read_sync(p: Path) -> Dict[str, Any]:
        nonlocal read_count
        read_count += 1
        return {"value": 42}

    with (
        patch(
            "configstream.server.utils._read_json_file",
            side_effect=mock_read_sync,
        ),
        patch(
            "configstream.server.utils.os.path.getmtime",
            return_value=fixed_mtime,
        ),
    ):
        first = await _read_json_file_async(json_file)
        second = await _read_json_file_async(json_file)

    assert first == {"value": 42}
    assert second == {"value": 42}
    # Second call must be served from cache — no additional read
    assert (
        read_count == 1
    ), f"Expected 1 disk read total but got {read_count}. Cache lookup is broken."
