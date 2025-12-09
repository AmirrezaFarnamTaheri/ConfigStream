from playwright.sync_api import sync_playwright
import time
import subprocess
import sys
import os

def run_verification():
    # Start server
    proc = subprocess.Popen([sys.executable, "-m", "http.server", "8080", "--directory", "frontend"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2) # Wait for server

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # 1. Index
            print("Navigating to index.html...")
            page.goto("http://localhost:8080/index.html")
            page.screenshot(path="verification_index.png")

            # Check links
            print("Checking navigation links...")

            # About
            about_link = page.get_by_role("link", name="About")
            # expect(about_link).to_have_attribute("href", "about.html") # Playwright check
            href = about_link.get_attribute("href")
            if href != "about.html":
                print(f"ERROR: About link href is {href}, expected about.html")
                sys.exit(1)

            # Wiki
            wiki_link = page.get_by_role("link", name="Wiki")
            href = wiki_link.get_attribute("href")
            if href != "wiki.html":
                print(f"ERROR: Wiki link href is {href}, expected wiki.html")
                sys.exit(1)

            # Navigate to About
            print("Clicking About...")
            about_link.click()
            page.wait_for_load_state("networkidle")
            if "about.html" not in page.url:
                print(f"ERROR: URL is {page.url}, expected .../about.html")
                sys.exit(1)
            page.screenshot(path="verification_about.png")

            # Check About page back link
            print("Checking back link on About page...")
            home_link = page.get_by_role("link", name="Home")
            href = home_link.get_attribute("href")
            if href != "index.html":
                print(f"ERROR: Home link on About page is {href}, expected index.html")
                sys.exit(1)

            print("SUCCESS: Navigation verified.")

            browser.close()
    finally:
        proc.terminate()

if __name__ == "__main__":
    run_verification()
