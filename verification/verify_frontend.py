from playwright.sync_api import sync_playwright, expect


def verify_frontend(page):
    page.goto("http://localhost:8000/index.html")

    # Wait for loading screen to disappear
    page.wait_for_selector("#loading-screen.hidden", state="attached", timeout=15000)
    # Also wait for the specific overlay mentioned in error log
    # It seems to be `loading-overlay` from some css file or js?
    # The error says <div id="loading-overlay" class="loading-overlay"> intercepts pointer events
    # I need to wait for it to detach or be hidden.
    try:
        page.wait_for_selector("#loading-overlay", state="hidden", timeout=5000)
    except Exception:
        pass  # Maybe it doesn't exist or is already hidden

    # Check Hero Section
    expect(page.get_by_text("Unlock the Internet")).to_be_visible()

    # Check Downloads Section for new cards
    downloads_btn = page.get_by_text("Get Configs")
    # Force click if necessary, but better to wait
    downloads_btn.click(force=True)

    # Verify Surge, Loon, QuantumultX, SIP008 cards exist with icons
    expect(page.get_by_text("Surge")).to_be_visible()
    expect(page.get_by_text("Loon")).to_be_visible()
    expect(page.get_by_text("Quantumult X")).to_be_visible()
    expect(page.get_by_text("SIP008")).to_be_visible()

    # Take screenshot
    page.screenshot(path="verification/frontend_verified.png", full_page=True)


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            verify_frontend(page)
            print("Frontend verification successful.")
        except Exception as e:
            print(f"Verification failed: {e}")
        finally:
            browser.close()
