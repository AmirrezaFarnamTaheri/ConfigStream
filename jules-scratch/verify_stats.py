
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Capture console messages
        page.on('console', lambda msg: print(f"Browser Console: {msg.text}"))

        await page.goto('http://localhost:8000')
        await page.wait_for_load_state('networkidle')
        await page.screenshot(path='jules-scratch/stats_page.png')
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
