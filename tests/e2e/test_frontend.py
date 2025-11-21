import pytest
from playwright.sync_api import Page, expect
import re
import json


# Remove all asyncio markers, let pytest-playwright handle loop injection
@pytest.mark.e2e
def test_homepage_loads(page: Page):
    """Test that the homepage loads and critical elements are visible."""
    import os

    cwd = os.getcwd()
    url = f"file://{cwd}/frontend/index.html"

    page.goto(url)
    expect(page).to_have_title("ConfigStream - Your Gateway to the Open Internet")

    # Check for the Logo
    logo = page.locator(".header-logo-text")
    expect(logo).to_be_visible()

    # Check for the "Browse Proxies" button
    btn = page.locator("text=Browse Proxies")
    expect(btn).to_be_visible()


@pytest.mark.e2e
def test_pwa_manifest_link(page: Page):
    import os

    cwd = os.getcwd()
    url = f"file://{cwd}/frontend/index.html"
    page.goto(url)

    # Check manifest link
    manifest = page.locator('link[rel="manifest"]')
    expect(manifest).to_have_count(1)
    href = manifest.get_attribute("href")
    assert href == "manifest.json"


@pytest.mark.e2e
def test_widgets_presence(page: Page):
    import os

    cwd = os.getcwd()
    url = f"file://{cwd}/frontend/analytics.html"

    # Mock the metadata request data
    mock_data = {
        "last_updated_utc": "2023-01-01T12:00:00Z",
        "total_proxies": 100,
        "total_working": 50,
        "total_fetched": 200,
        "duration_seconds": 10.5,
        "protocols": {"vmess": 50, "vless": 50},
        "countries": {"US": 50, "DE": 50},
        "country_stats": {"US": 50, "DE": 50},
        "latency_distribution": {"fast": 10, "medium": 20, "slow": 10, "very_slow": 10},
        "protocol_colors": {"vmess": "#ff0000", "vless": "#00ff00"},
    }

    mock_json = json.dumps(mock_data)

    # Inject a mock fetch function that returns our data for metadata.json
    # We do this before navigation so it's available when the page loads
    # We mock /api/stats AND /files/metadata.json to cover both paths in utils.js
    page.add_init_script(
        f"""
        const originalFetch = window.fetch;
        window.fetch = async (url, options) => {{
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

    page.goto(url)

    # Globe Viz (Replaces Map Container in V4)
    expect(page.locator("#globe-viz")).to_be_visible()

    # Stats cards should be updated
    # Wait for the loading class to be removed to ensure JS processed it
    expect(page.locator("#totalSourced")).not_to_have_class(re.compile(r"loading"))

    expect(page.locator("#totalSourced")).to_contain_text("200")
    expect(page.locator("#totalConfigs")).to_contain_text("100")

    # Protocol Chart
    # Wait for chart to be rendered (canvas present)
    expect(page.locator("#protocolChart")).to_be_visible()
