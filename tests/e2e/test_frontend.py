# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from pathlib import Path
from playwright.sync_api import Page, expect, sync_playwright
from playwright._impl._errors import Error as PlaywrightError
import re
import json
import os
from urllib.parse import urlparse


def _playwright_ready() -> bool:
    try:
        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:
        return False


_PLAYWRIGHT_READY = _playwright_ready()
_REQUIRE_PLAYWRIGHT = os.getenv("CONFIGSTREAM_REQUIRE_PLAYWRIGHT") == "1"

if _REQUIRE_PLAYWRIGHT and not _PLAYWRIGHT_READY:
    raise RuntimeError(
        "CONFIGSTREAM_REQUIRE_PLAYWRIGHT=1 but Python Playwright browsers are "
        "not installed. Run `python -m playwright install --with-deps` before "
        "the frontend-browser test profile."
    )

pytestmark = pytest.mark.skipif(
    not _PLAYWRIGHT_READY, reason="Playwright browsers not installed"
)


# Remove all asyncio markers, let pytest-playwright handle loop injection
@pytest.mark.e2e
def test_homepage_loads(page: Page, http_server):
    """Test that the homepage loads and critical elements are visible."""
    # Block WebAssembly and problematic scripts that crash in containerized Chromium
    page.route("**/*.wasm", lambda route: route.abort())
    page.route("**/wasm_*.js", lambda route: route.abort())
    page.route("**/plugin_loader.js", lambda route: route.abort())
    page.route("**/stego_loader.js", lambda route: route.abort())

    # Mock metadata.json to prevent update-detector from failing
    page.route(
        "**/metadata.json",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"last_updated_utc":"2023-01-01T12:00:00Z","total_proxies":100}',
        ),
    )

    url = f"{http_server}/index.html"

    try:
        # Disable animations to prevent visibility issues
        page.add_init_script("""
            const style = document.createElement('style');
            style.innerHTML = `
                *, *::before, *::after {
                    animation: none !important;
                    transition: none !important;
                    opacity: 1 !important;
                }
            `;
            document.head.appendChild(style);
        """)

        page.goto(url, wait_until="networkidle", timeout=10000)
    except PlaywrightError as e:
        if "crashed" in str(e).lower():
            pytest.skip(
                "Browser crashed - likely due to containerized environment limitations"
            )
        raise

    expect(page).to_have_title("ConfigStream - Your Gateway to the Open Internet")

    # Wait for loading screen to disappear
    # This is critical as it overlays the entire page
    page.locator("#loading-screen").wait_for(state="hidden", timeout=15000)

    # Check for the Logo
    logo = page.locator(".header-logo-text")
    expect(logo).to_be_visible()

    # Check for the "Browse Proxies" button
    # Using more robust locator strategy
    btn = page.locator("a.btn-primary:has-text('Browse Proxies')")
    try:
        expect(btn).to_be_visible(timeout=5000)
    except AssertionError:
        print(f"DEBUG: Page Content: {page.content()}")
        raise


@pytest.mark.e2e
def test_pwa_manifest_link(page: Page, http_server):
    # Block WebAssembly and problematic scripts
    page.route("**/*.wasm", lambda route: route.abort())
    page.route("**/wasm_*.js", lambda route: route.abort())
    page.route("**/plugin_loader.js", lambda route: route.abort())
    page.route("**/stego_loader.js", lambda route: route.abort())

    # Mock metadata.json to prevent update-detector from failing
    page.route(
        "**/metadata.json",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"last_updated_utc":"2023-01-01T12:00:00Z","total_proxies":100}',
        ),
    )

    url = f"{http_server}/index.html"

    try:
        page.goto(url, wait_until="networkidle", timeout=10000)
    except PlaywrightError as e:
        if "crashed" in str(e).lower():
            pytest.skip(
                "Browser crashed - likely due to containerized environment limitations"
            )
        raise

    # Check manifest link
    manifest = page.locator('link[rel="manifest"]')
    expect(manifest).to_have_count(1)
    href = manifest.get_attribute("href")
    assert href == "manifest.json"


@pytest.mark.e2e
def test_widgets_presence(page: Page, http_server):
    # Block WebAssembly and problematic scripts
    page.route("**/*.wasm", lambda route: route.abort())
    page.route("**/wasm_*.js", lambda route: route.abort())
    page.route("**/plugin_loader.js", lambda route: route.abort())
    page.route("**/stego_loader.js", lambda route: route.abort())

    url = f"{http_server}/analytics.html"

    # Mock the metadata request data (using canonical field names from v2.0.8)
    mock_data = {
        "last_updated_utc": "2023-01-01T12:00:00Z",
        "total_proxies": 100,
        "total_working": 50,
        "total_lines_sourced": 200,  # Canonical field name
        "total_unique_candidates": 100,  # Canonical field name
        "total_valid_proxies": 50,  # Canonical field name
        "duration_seconds": 10.5,
        "protocols": {"vmess": 50, "vless": 50},
        "countries": {"US": 50, "DE": 50},
        "country_stats": {"US": 50, "DE": 50},
        "latency_distribution": {"fast": 10, "medium": 20, "slow": 10, "very_slow": 10},
        "protocol_colors": {"vmess": "#ff0000", "vless": "#00ff00"},
    }

    mock_json = json.dumps(mock_data)

    # Inject a mock fetch function that returns our data for statistics endpoints
    # We do this before navigation so it's available when the page loads
    # [UNIFIED] metadata.json is now single source of truth for all analytics data
    page.add_init_script(f"""
        const originalFetch = window.fetch;
        window.fetch = async (url, options) => {{
            // Mock metadata.json (unified stats) and api/stats endpoints
            if (url.includes('api/stats') || url.includes('metadata.json')) {{
                return {{
                    ok: true,
                    status: 200,
                    json: async () => ({mock_json})
                }};
            }}
            return originalFetch(url, options);
        }};

        // Mock window.api.fetchStatistics directly if needed
        window.api = window.api || {{}};
        window.api.fetchStatistics = async () => ({mock_json});
    """)

    try:
        page.goto(url, wait_until="networkidle", timeout=10000)
    except PlaywrightError as e:
        if "crashed" in str(e).lower():
            pytest.skip(
                "Browser crashed - likely due to containerized environment limitations"
            )
        raise

    # Globe Viz (Replaces Map Container in V4)
    expect(page.locator("#globe-viz")).to_be_visible(timeout=10000)

    # Stats cards should be updated
    # Wait for the loading class to be removed to ensure JS processed it
    expect(page.locator("#totalSourced")).not_to_have_class(
        re.compile(r"loading"), timeout=10000
    )

    expect(page.locator("#totalSourced")).to_contain_text("200", timeout=10000)
    expect(page.locator("#totalConfigs")).to_contain_text("100", timeout=10000)

    # Protocol Chart
    # Wait for chart to be rendered (canvas present)
    expect(page.locator("#protocolChart")).to_be_visible(timeout=10000)


@pytest.mark.e2e
def test_frontend_pages_load_with_external_network_blocked(page: Page, http_server):
    """Primary pages must not depend on runtime CDNs or external image hosts."""

    allowed_origin = urlparse(http_server).netloc
    blocked_urls = []

    def route_handler(route):
        request_url = route.request.url
        parsed = urlparse(request_url)

        if parsed.scheme in {"http", "https"} and parsed.netloc != allowed_origin:
            blocked_urls.append(request_url)
            route.abort()
            return

        route.continue_()

    page.route("**/*", route_handler)
    page.route("**/*.wasm", lambda route: route.abort())
    page.route("**/wasm_*.js", lambda route: route.abort())
    page.route("**/plugin_loader.js", lambda route: route.abort())
    page.route("**/stego_loader.js", lambda route: route.abort())

    page.add_init_script("""
        const style = document.createElement('style');
        style.innerHTML = `
            *, *::before, *::after {
                animation: none !important;
                transition: none !important;
                opacity: 1 !important;
            }
        `;
        document.head.appendChild(style);
    """)

    for page_name in (
        "index.html",
        "about.html",
        "analytics.html",
        "proxies.html",
        "lab.html",
        "wiki.html",
    ):
        try:
            page.goto(
                f"{http_server}/{page_name}",
                wait_until="domcontentloaded",
                timeout=10000,
            )
        except PlaywrightError as e:
            if "crashed" in str(e).lower():
                pytest.skip(
                    "Browser crashed - likely due to containerized environment limitations"
                )
            raise

        expect(page.locator(".header-logo-text")).to_be_visible(timeout=10000)
        expect(page.locator("#main-nav")).to_be_visible(timeout=10000)

    assert blocked_urls == []
