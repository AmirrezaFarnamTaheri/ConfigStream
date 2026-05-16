# SPDX-License-Identifier: AGPL-3.0-or-later
"""Take screenshots of a deployed GitHub Pages site for evidence."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright


async def take_screenshots(url: str, output_dir: str) -> None:
    """Capture deployment evidence screenshots for primary public pages."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    base_url = url.rstrip("/") + "/"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        # 1. Dashboard
        print(f"Capturing dashboard: {base_url}")
        await page.goto(base_url, wait_until="networkidle")
        await asyncio.sleep(2)
        await page.screenshot(path=output_path / "dashboard.png", full_page=True)

        # 2. Analytics
        analytics_url = urljoin(base_url, "analytics.html")
        print(f"Capturing analytics: {analytics_url}")
        await page.goto(analytics_url, wait_until="networkidle")
        await asyncio.sleep(3)
        await page.screenshot(path=output_path / "analytics.png", full_page=True)

        # 3. Laboratory
        lab_url = urljoin(base_url, "lab.html")
        print(f"Capturing lab: {lab_url}")
        await page.goto(lab_url, wait_until="networkidle")
        await asyncio.sleep(2)
        await page.screenshot(path=output_path / "lab.png", full_page=True)

        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="GitHub Pages deployment URL")
    parser.add_argument(
        "--output-dir",
        default="evidence/screenshots",
        help="Directory to save screenshots",
    )
    args = parser.parse_args()

    asyncio.run(take_screenshots(args.url, args.output_dir))
