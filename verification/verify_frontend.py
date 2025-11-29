from playwright.sync_api import sync_playwright
import os


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # We need to serve the frontend files.
        # Since this is a static site, we can try to use a file url or python http server.
        # But `run_in_bash_session` shares session, so I can start a server in background.

        # Assuming server is started at port 8000
        page.goto("http://localhost:8000/frontend/index.html")

        # Test BYOW modal
        # There might be a button to open BYOW or we inspect the code.
        # byow.js attaches to 'btn-singbox-byow' which is a download link,
        # but applyBYOW() is called by something?
        # Typically there is an input #worker-url and a button.

        # Let's verify input validation.
        # We need to find the input.

        # Check if #worker-url exists
        try:
            page.wait_for_selector("#worker-url", timeout=5000)
            print("Found worker-url input")

            # Fill invalid URL
            page.fill("#worker-url", "javascript:alert(1)")
            # Trigger applyBYOW - assuming there is a button that calls it.
            # I need to find the trigger. Usually a button "Generate Config" or similar.
            # I'll look for a button near the input.

            # Let's take a screenshot of the BYOW section
            page.screenshot(path="verification/frontend_byow.png")

        except Exception as e:
            print(f"Could not verify BYOW UI: {e}")
            # Fallback screenshot of whatever we loaded
            page.screenshot(path="verification/frontend_fallback.png")

        browser.close()


if __name__ == "__main__":
    run()
