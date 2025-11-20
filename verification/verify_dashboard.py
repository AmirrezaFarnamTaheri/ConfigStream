import os
from playwright.sync_api import sync_playwright


def verify_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Mock API responses
        page.route(
            "**/api/stats",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{"total_proxies": 1000, "total_working": 500, "total_fetched": 2000, "duration_seconds": 60, "last_updated_utc": "2023-10-27T10:00:00Z", "protocols": {"vmess": 300, "vless": 200}, "countries": {"US": 100, "DE": 50}}',
            ),
        )

        page.route(
            "**/api/proxies",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='[{"protocol": "vmess", "address": "1.2.3.4", "port": 443, "country_code": "US"}]',
            ),
        )

        # Get absolute path to index.html
        cwd = os.getcwd()
        index_path = os.path.join(cwd, "frontend/index.html")

        print(f"Loading: file://{index_path}")
        page.goto(f"file://{index_path}")

        # Wait for main container
        page.wait_for_selector(".container")

        # Allow JS to execute and render charts/maps (mocked in our case as basic implementation)
        page.wait_for_timeout(1000)

        # Take full page screenshot
        screenshot_path = "verification/dashboard.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        browser.close()


if __name__ == "__main__":
    verify_dashboard()
