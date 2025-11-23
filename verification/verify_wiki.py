
import os
from playwright.sync_api import sync_playwright, expect

def verify_wiki(page):
    # Go to Wiki page (assuming local file access)
    file_path = os.path.abspath("frontend/wiki.html")
    page.goto(f"file://{file_path}")

    # Wait for Wiki content to load
    # The sidebar is populated by JS
    page.wait_for_selector(".wiki-nav-item")

    # Click on 'Introduction'
    page.click("text=Introduction")

    # Wait for content
    # Content is loaded via fetch from 'wiki/01-introduction.md'
    # Since we are using file:// protocol, fetch might fail due to CORS or path resolution
    # However, let's see if the error state or loading state is visible.
    # If fetch fails, it shows "Error Loading Documentation"

    # Take screenshot
    page.screenshot(path="/home/jules/verification/wiki.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_wiki(page)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()
