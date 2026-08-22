# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression contracts for sortable headers and service-worker cache migration."""

from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]


def test_sortable_headers_keep_column_semantics_and_use_native_buttons() -> None:
    html = (ROOT / "frontend/proxies.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    headers = soup.select("th.sortable")

    assert len(headers) == 4
    for header in headers:
        assert header.get("aria-sort") in {"none", "ascending", "descending"}
        assert header.get("role") is None
        assert header.get("tabindex") is None
        assert header.get("data-sort") is None
        button = header.select_one('button.sort-button[type="button"][data-sort]')
        assert button is not None
        assert button.get_text(strip=True)
        icon = button.select_one('[data-feather="chevron-down"]')
        assert icon is not None
        assert icon.get("aria-hidden") == "true"


def test_sorting_uses_native_button_click_without_custom_keydown() -> None:
    source = (ROOT / "frontend/assets/js/proxies.js").read_text(encoding="utf-8")
    setup_sorting = source.split("function setupSorting()", 1)[1].split(
        "function sortProxies()", 1
    )[0]

    assert "button.addEventListener('click', activateSort)" in setup_sorting
    assert "button.dataset.sort" in setup_sorting
    assert "addEventListener('keydown'" not in setup_sorting
    assert "th.addEventListener('click'" not in setup_sorting


def test_service_worker_fallback_and_cleanup_share_managed_namespaces() -> None:
    source = (ROOT / "frontend/service-worker.js").read_text(encoding="utf-8")

    assert "`${CACHE_PREFIX}${CACHE_VERSION}`" in source
    assert "const LEGACY_CACHE_PREFIX = 'configstream-v';" in source
    assert "cacheName.startsWith(CACHE_PREFIX)" in source
    assert "cacheName.startsWith(LEGACY_CACHE_PREFIX)" in source
    assert "cacheName !== CACHE_NAME" in source
