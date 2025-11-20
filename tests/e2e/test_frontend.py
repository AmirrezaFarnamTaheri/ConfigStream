import pytest
from playwright.sync_api import Page, expect


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
    url = f"file://{cwd}/frontend/analytics.html"  # Changed to analytics.html
    page.goto(url)

    # Map Container (Leaflet map)
    expect(page.locator("#map-container")).to_be_visible()

    # Protocol Chart
    expect(page.locator("#protocolChart")).to_be_visible()
