from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch()
    context = browser.new_context(
        viewport={'width': 375, 'height': 812},
        is_mobile=True,
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1'
    )
    page = context.new_page()
    page.goto("http://localhost:8000/proxies.html")
    page.click('.accordion-header')
    page.wait_for_selector('.accordion-content[style="grid-template-rows: 1fr;"]')
    page.screenshot(path="jules-scratch/verification/proxies-mobile-refined.png")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
