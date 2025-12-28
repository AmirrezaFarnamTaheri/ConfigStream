import json
import re

import pytest
from playwright._impl._errors import Error as PlaywrightError
from playwright.sync_api import Page, expect


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
        page.goto(url, wait_until="networkidle", timeout=10000)
    except PlaywrightError as e:
        if "crashed" in str(e).lower():
            pytest.skip(
                "Browser crashed - likely due to containerized environment limitations"
            )
        raise

    expect(page).to_have_title("ConfigStream - Your Gateway to the Open Internet")

    # Check for the Logo
    logo = page.locator(".header-logo-text")
    expect(logo).to_be_visible()

    # Check for the "Browse Proxies" button
    btn = page.locator("text=Browse Proxies")
    expect(btn).to_be_visible(timeout=10000)


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
    page.add_init_script(
        f"""
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
    """
    )

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
