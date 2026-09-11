# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
from unittest.mock import patch

import pytest

from configstream.test_cache import TestResultCache


def test_relative_cache_path_resolves_against_project_root(tmp_path):
    project_root = tmp_path / "checkout"
    project_root.mkdir()

    with patch("configstream.test_cache._find_project_root", return_value=project_root):
        cache = TestResultCache("data/test_cache.json", ttl_seconds=60)

    assert cache.db_path == (project_root / "data/test_cache.json").resolve()


def test_relative_cache_path_uses_platform_cache_without_checkout(tmp_path):
    cache_root = tmp_path / "user-cache"

    with (
        patch("configstream.test_cache._find_project_root", return_value=None),
        patch("configstream.test_cache.user_cache_path", return_value=cache_root),
    ):
        cache = TestResultCache("data/test_cache.json", ttl_seconds=60)

    assert cache.db_path == (cache_root / "data/test_cache.json").resolve()


def test_absolute_cache_path_is_preserved(tmp_path):
    cache_path = tmp_path / "cache.json"
    cache = TestResultCache(cache_path, ttl_seconds=60)
    assert cache.db_path == cache_path.resolve()


def test_oversized_cache_file_fails_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_path = tmp_path / "cache.json"
    cache_path.write_text('{"entry": {"tested_at": 1}}', encoding="utf-8")
    monkeypatch.setattr("configstream.test_cache.MAX_CACHE_FILE_BYTES", 1)
    cache = TestResultCache(cache_path, ttl_seconds=60)
    assert cache._cache == {}
