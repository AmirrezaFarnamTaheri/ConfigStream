# SPDX-License-Identifier: AGPL-3.0-or-later
from unittest.mock import patch

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
