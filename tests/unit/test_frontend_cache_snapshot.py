# SPDX-License-Identifier: AGPL-3.0-or-later
"""Frontend cache snapshot identity checks."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_proxy_array_cache_uses_metadata_snapshot_hash() -> None:
    cache_manager_js = (
        REPO_ROOT / "frontend/assets/js/cache-manager.js"
    ).read_text(encoding="utf-8")
    main_js = (REPO_ROOT / "frontend/assets/js/main.js").read_text(encoding="utf-8")

    assert "window.CONFIGSTREAM_PROXY_SNAPSHOT_HASH" in main_js
    assert "metadata?.proxies_snapshot_hash" in main_js
    assert "Array.isArray(data) && url.includes('api/proxies')" in cache_manager_js
    assert "window.CONFIGSTREAM_PROXY_SNAPSHOT_HASH" in cache_manager_js
