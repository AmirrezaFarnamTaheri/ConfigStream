import os
from playwright.sync_api import sync_playwright, expect

def verify_wasm_button():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://localhost:8000/proxies.html")

        # Check if WASM button exists
        wasm_btn = page.locator("#testWasm")
        expect(wasm_btn).to_be_visible()

        # Check if text is correct
        expect(wasm_btn).to_contain_text("Test (WASM)")

        # Take screenshot
        os.makedirs("verification", exist_ok=True)
        page.screenshot(path="verification/proxies_wasm_btn.png")

        browser.close()

if __name__ == "__main__":
    verify_wasm_button()
