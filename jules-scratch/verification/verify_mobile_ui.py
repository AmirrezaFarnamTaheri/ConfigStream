import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # Set a mobile viewport
        context = await browser.new_context(viewport={"width": 375, "height": 667})
        page = await context.new_page()

        # Start a local server
        # In a real scenario, you'd start a server here.
        # For this example, we'll use file:// protocol.
        # This might cause issues with some scripts, but it's fine for this verification.

        # Verify the hamburger menu
        await page.goto("file:///app/index.html")
        await page.click("#mobile-nav-toggle")
        await page.wait_for_selector(".nav-open")
        await page.screenshot(path="jules-scratch/verification/mobile-nav.png")

        # Verify the card alignment
        await page.goto("file:///app/proxies.html")
        await page.screenshot(path="jules-scratch/verification/card-alignment.png")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
