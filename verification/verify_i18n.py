from playwright.sync_api import sync_playwright
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Determine the absolute path to the about.html file
        cwd = os.getcwd()
        file_path = f"file://{cwd}/frontend/about.html"
        print(f"Navigating to {file_path}")

        page.goto(file_path)

        # Wait for the i18n to load and update the page
        page.wait_for_load_state("networkidle")

        # Check if the text content of the list items is correct and HTML is rendered
        # Specifically checking for the "Hybrid Engine" text which contains <strong>
        hybrid_engine = page.locator('li[data-i18n="about.arch.hybrid"]')

        # Wait for the element to be visible
        hybrid_engine.wait_for(state="visible")

        print("Checking content of 'Hybrid Engine' list item...")
        # Get the inner HTML to verify <strong> tags are present
        content = hybrid_engine.inner_html()
        print(f"Content: {content}")

        if "<strong>" in content:
            print("SUCCESS: HTML tags are present.")
        else:
            print("FAILURE: HTML tags are NOT present.")

        # Take a screenshot of the Architecture section
        screenshot_path = "verification/about_page_arch.png"
        page.locator('.feature-list').screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")

        browser.close()

if __name__ == "__main__":
    run()
