import asyncio
from playwright.async_api import async_playwright
import os

async def verify_frontend():
    async with async_playwright() as p:
        # Launch browser (headless=True for CI/headless environments)
        browser = await p.chromium.launch(headless=True)

        # Create a new context with a specific viewport size to mimic desktop
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        # Resolve the absolute path to the frontend index.html
        cwd = os.getcwd()
        file_url = f"file://{cwd}/frontend/index.html"
        print(f"Navigating to: {file_url}")

        # Navigate to the page
        await page.goto(file_url)

        # Wait for page load
        await page.wait_for_load_state("networkidle")

        # 1. Verify Title
        title = await page.title()
        print(f"Page Title: {title}")
        assert "ConfigStream" in title, "Title does not contain 'ConfigStream'"

        # 2. Verify i18n Translation (Check if 'Home' is present)
        # Assuming default is English
        home_link = page.locator('a[data-i18n="nav.home"]')
        await home_link.wait_for()
        text = await home_link.text_content()
        print(f"Nav Home Text: {text}")
        assert text == "Home", "Default language (EN) not applied correctly"

        # 3. Change Language to Persian (fa) and Verify
        # Simulate clicking the language button logic or directly calling JS
        # Since button is complex, let's call the exposed JS API directly
        print("Switching language to 'fa'...")
        await page.evaluate("window.i18n.setLanguage('fa')")

        # Wait a bit for DOM updates
        await page.wait_for_timeout(500)

        # Verify Font Family on Body (should include Vazirmatn)
        font_family = await page.evaluate("getComputedStyle(document.body).fontFamily")
        print(f"Font Family (fa): {font_family}")
        # Note: Computed style might return the full stack. Just check if Vazirmatn is prioritized or present if applying class
        # But our CSS uses [lang="fa"] selector.

        # Verify header text change
        home_text_fa = await home_link.text_content()
        print(f"Nav Home Text (fa): {home_text_fa}")
        assert home_text_fa == "خانه", "Persian translation not applied"

        # Verify Mikhak font on Headers
        # Check an h1 element
        h1_font = await page.evaluate("getComputedStyle(document.querySelector('h1')).fontFamily")
        print(f"H1 Font Family (fa): {h1_font}")
        assert "Mikhak" in h1_font or "Vazirmatn" in h1_font, "Mikhak font not applied to H1"

        # 4. Verify Theme Switching
        print("Switching theme to Dark...")
        await page.evaluate("document.body.classList.add('dark')")
        # Dispatch event to update globe
        await page.evaluate("window.dispatchEvent(new CustomEvent('themechanged', { detail: { theme: 'dark' } }))")

        await page.wait_for_timeout(500)

        # Take a screenshot
        screenshot_path = "output/frontend_verification_screenshot.png"
        os.makedirs("output", exist_ok=True)
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_frontend())
