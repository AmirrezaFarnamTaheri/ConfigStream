from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Test About Page via HTTP
        print("Navigating to http://localhost:8000/about/")
        page.goto("http://localhost:8000/about/")
        page.wait_for_selector(".header")
        # Wait a bit for fonts/animations
        page.wait_for_timeout(1000)
        page.screenshot(path="verification/verification_about_http.png")

        # Test Wiki Page via HTTP
        print("Navigating to http://localhost:8000/wiki/")
        page.goto("http://localhost:8000/wiki/")
        page.wait_for_selector(".header")
        page.wait_for_timeout(1000)
        page.screenshot(path="verification/verification_wiki_http.png")

        browser.close()

if __name__ == "__main__":
    run()