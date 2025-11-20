from playwright.sync_api import sync_playwright


def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the local server
        page.goto("http://localhost:8080/index.html")

        # Verify Title
        assert "ConfigStream" in page.title()

        # Verify Header Elements
        page.wait_for_selector(".header-logo")

        # Verify Theme Toggle works
        theme_btn = page.locator("#theme-switcher")
        theme_btn.click()
        page.wait_for_timeout(500)  # Wait for transition

        # Take screenshot
        screenshot_path = "verification/frontend_verify.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        browser.close()


if __name__ == "__main__":
    verify_frontend()
