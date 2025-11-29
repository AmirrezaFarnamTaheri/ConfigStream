from playwright.sync_api import sync_playwright

def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Go to home page
        page.goto("http://localhost:8000/index.html")
        page.wait_for_load_state("networkidle")

        # Screenshot Home Page Top
        page.screenshot(path="verification/home_top.png")

        # Verify Info Cards and Dynamic Downloads
        # Scroll to downloads section
        downloads = page.locator("#downloads")
        downloads.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        # Check Client Selector existence
        selector = page.locator("#client-selector")
        if selector.count() > 0:
            print("Client selector found")
            # Select 'Surge'
            selector.select_option("surge")
            page.wait_for_timeout(200)
            page.screenshot(path="verification/dynamic_downloads_surge.png")

            # Select 'Quantumult X'
            selector.select_option("quantumultx")
            page.wait_for_timeout(200)
            page.screenshot(path="verification/dynamic_downloads_qx.png")
        else:
            print("Client selector NOT found")

        # Verify Header consistency
        page.screenshot(path="verification/header.png", clip={"x": 0, "y": 0, "width": 1280, "height": 100})

        # Check Favicon (can't screenshot easily but can check attribute)
        favicon = page.locator("link[rel='icon']").first
        print(f"Favicon href: {favicon.get_attribute('href')}")

        browser.close()

if __name__ == "__main__":
    verify_frontend()
