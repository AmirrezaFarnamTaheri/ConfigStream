from playwright.sync_api import sync_playwright, expect
import time
import re

def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the local server
        page.goto("http://localhost:8080/frontend/index.html")
        expect(page).to_have_title("ConfigStream - Your Gateway to the Open Internet")

        # Verify Live Feed on Index
        feed = page.locator("#pipeline-feed")
        expect(feed).to_be_visible()

        # Verify Widgets are NOT on Index
        map_widget = page.locator("#world-map-widget")
        expect(map_widget).not_to_be_visible()

        # Navigate to Statistics
        page.goto("http://localhost:8080/frontend/statistics.html")

        # Verify Widgets are on Statistics
        map_widget = page.locator("#world-map-widget")
        expect(map_widget).to_be_visible()

        chart_widget = page.locator("#historical-chart-widget")
        expect(chart_widget).to_be_visible()

        # Verify Leaflet Map Loaded
        expect(map_widget).to_have_class(re.compile(r"leaflet-container"))

        time.sleep(1)
        page.screenshot(path="verification/dashboard_stats.png", full_page=True)
        browser.close()

if __name__ == "__main__":
    verify_frontend()
