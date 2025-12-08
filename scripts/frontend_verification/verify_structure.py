import asyncio
from playwright.async_api import async_playwright
import os

async def verify_ui_structure():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        cwd = os.getcwd()

        # 1. Verify Wiki Page
        wiki_url = f"file://{cwd}/frontend/wiki/index.html"
        print(f"Checking Wiki Page: {wiki_url}")
        try:
            await page.goto(wiki_url)
            title = await page.title()
            print(f"Wiki Title: {title}")
            assert "Wiki" in title or "Documentation" in title
            # Check if assets loaded (e.g. check a style property that depends on style.css)
            color = await page.evaluate("getComputedStyle(document.body).backgroundColor")
            print(f"Wiki Body Background: {color}")
            # If style.css loaded, body bg shouldn't be default white (unless theme is light/white)
            # but let's check if the link tag is correct
            css_href = await page.get_attribute("link[rel='stylesheet'][href*='style.css']", "href")
            print(f"Wiki CSS Path: {css_href}")
            assert "../assets/css/style.css" in css_href
        except Exception as e:
            print(f"Wiki Page Verification Failed: {e}")
            raise e

        # 2. Verify About Page
        about_url = f"file://{cwd}/frontend/about/index.html"
        print(f"Checking About Page: {about_url}")
        try:
            await page.goto(about_url)
            title = await page.title()
            print(f"About Title: {title}")
            assert "ConfigStream" in title
            # Check navigation link back to home
            home_link = await page.get_attribute("a[data-i18n='nav.home']", "href")
            print(f"About -> Home Link: {home_link}")
            assert "../index.html" in home_link
        except Exception as e:
            print(f"About Page Verification Failed: {e}")
            raise e

        print("UI Structure Verification Passed")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_ui_structure())
