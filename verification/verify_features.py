import os
from playwright.sync_api import sync_playwright

def verify_features():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Mock API responses
        page.route("**/api/stats", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"total_proxies": 1000, "total_working": 500, "total_fetched": 2000, "duration_seconds": 60, "last_updated_utc": "2023-10-27T10:00:00Z", "protocols": {"vmess": 300, "vless": 200}, "countries": {"US": 100, "DE": 50}}'
        ))

        # Get absolute path to index.html
        cwd = os.getcwd()
        index_path = os.path.join(cwd, "frontend/index.html")

        print(f"Loading: file://{index_path}")
        page.goto(f"file://{index_path}")

        # Wait for main container
        page.wait_for_selector(".container")

        # Allow JS to execute and render charts/maps
        page.wait_for_timeout(1000)

        # Verify Chosen 1000 Section
        try:
            page.wait_for_selector(".chosen-section", timeout=2000)
            print("Found Chosen 1000 section")
        except:
            print("ERROR: Chosen 1000 section not found")

        # Verify Map
        try:
            page.wait_for_selector(".map-tile", timeout=2000)
            print("Found Map Tiles")
        except:
            print("ERROR: Map not rendered")

        # Take full page screenshot
        screenshot_path = "verification/features_check.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        browser.close()

if __name__ == "__main__":
    verify_features()
