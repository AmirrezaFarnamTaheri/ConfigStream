# SPDX-License-Identifier: AGPL-3.0-or-later
"""Rendered-pixel smoke coverage for the public homepage."""

import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright


def _playwright_ready() -> bool:
    try:
        with sync_playwright() as playwright:
            if Path(playwright.chromium.executable_path).exists():
                return True
    except Exception:
        pass

    configured_browser_root = os.getenv("PLAYWRIGHT_BROWSERS_PATH", "")
    if not configured_browser_root or configured_browser_root == "0":
        local_app_data = os.getenv("LOCALAPPDATA")
        if not local_app_data:
            return False
        browser_root = Path(local_app_data) / "ms-playwright"
    else:
        browser_root = Path(configured_browser_root)

    return any(
        path.exists()
        for path in browser_root.glob("chromium-*/chrome-win64/chrome.exe")
    )


pytestmark = pytest.mark.skipif(
    not _playwright_ready(), reason="Playwright browsers not installed"
)


@pytest.mark.e2e
def test_homepage_screenshot_smoke(page: Page, http_server):
    page.route("**/*.wasm", lambda route: route.abort())
    page.route("**/wasm_*.js", lambda route: route.abort())
    page.route("**/globe.gl.min.js", lambda route: route.abort())
    page.route("**/plugin_loader.js", lambda route: route.abort())
    page.route("**/stego_loader.js", lambda route: route.abort())
    page.route(
        "**/metadata.json",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"last_updated_utc":"2023-01-01T12:00:00Z","total_proxies":100}',
        ),
    )
    page.add_init_script("""
        const style = document.createElement('style');
        style.innerHTML = `
            *, *::before, *::after {
                animation: none !important;
                transition: none !important;
                caret-color: transparent !important;
            }
        `;
        document.head.appendChild(style);
        """)

    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(f"{http_server}/index.html", wait_until="networkidle", timeout=10000)
    page.locator("#loading-screen").wait_for(state="hidden", timeout=15000)
    expect(page.locator(".header-logo-text")).to_be_visible()
    expect(page.locator("a.btn-primary:has-text('Browse Proxies')")).to_be_visible()

    screenshot = page.screenshot(full_page=True, animations="disabled")
    assert screenshot.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(screenshot) > 10_000
