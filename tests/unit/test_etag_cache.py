from __future__ import annotations

import json
from unittest.mock import patch

from configstream.etag_cache import ETAG_CACHE_PATH, load_etags, save_etags


def test_save_and_load_etags(tmp_path):
    """Verify that etags can be saved to and loaded from the cache."""
    cache_file = tmp_path / "etags.json"

    with patch("configstream.etag_cache.ETAG_CACHE_PATH", cache_file):

        # 1. Start with an empty cache
        assert load_etags() == {}

        # 2. Save some data
        etags_to_save = {
            "http://example.com/source1": {"etag": "etag1", "last-modified": "date1"},
            "http://example.com/source2": {"etag": "etag2"},
            "http://example.com/source3": {"last-modified": None},  # Should be filtered out
        }
        save_etags(etags_to_save)

        # 3. Verify the file content
        assert cache_file.exists()
        content = json.loads(cache_file.read_text())
        expected_content = {
            "http://example.com/source1": {"etag": "etag1", "last-modified": "date1"},
            "http://example.com/source2": {"etag": "etag2"},
        }
        assert content == expected_content

        # 4. Load the data and verify it matches
        loaded_etags = load_etags()
        assert loaded_etags == expected_content


def test_load_etags_nonexistent_file(tmp_path):
    """Verify that loading from a nonexistent cache file returns an empty dict."""
    cache_file = tmp_path / "nonexistent.json"
    with patch("configstream.etag_cache.ETAG_CACHE_PATH", cache_file):
        assert load_etags() == {}


def test_load_etags_invalid_json(tmp_path):
    """Verify that loading from a corrupt cache file returns an empty dict."""
    cache_file = tmp_path / "invalid.json"
    cache_file.write_text("this is not json")
    with patch("configstream.etag_cache.ETAG_CACHE_PATH", cache_file):
        assert load_etags() == {}
