import os
from playwright.sync_api import sync_playwright


def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the local server
        page.goto("http://localhost:8000/frontend/analytics.html")

        # Wait for analytics elements to load
        page.wait_for_selector("#map-container")
        page.wait_for_selector("canvas")

        # Take screenshot of Analytics page
        os.makedirs("verification", exist_ok=True)
        page.screenshot(path="verification/analytics.png", full_page=True)

        # Navigate to About page
        page.goto("http://localhost:8000/frontend/about.html")
        page.wait_for_selector("article.card")

        # Take screenshot of About page
        page.screenshot(path="verification/about.png", full_page=True)

        browser.close()


if __name__ == "__main__":
    verify_frontend()
