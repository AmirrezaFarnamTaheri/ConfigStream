# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import os
import sys
import threading
import http.server
import socketserver
from playwright.async_api import async_playwright

# Serve the frontend directory
PORT = 8082
DIRECTORY = "frontend"


def serve():
    try:
        os.chdir(DIRECTORY)
        Handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Serving at port {PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Server error: {e}")


async def verify_ui_async():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # 1. Index Page
        print("Visiting index.html...")
        try:
            await page.goto(f"http://localhost:{PORT}/index.html")
            await page.wait_for_load_state("networkidle")

            await page.screenshot(
                path="../frontend_verification_index_fa.png", full_page=True
            )
            print("Screenshot saved: frontend_verification_index_fa.png")

            # English Screenshot
            print("Switching to English for screenshot...")
            await page.evaluate("document.documentElement.lang = 'en'")
            # Wait for any potential re-rendering or animations
            await asyncio.sleep(0.5)
            await page.screenshot(
                path="../frontend_verification_index_en.png", full_page=True
            )

            # 2. Analytics Page
            print("Visiting analytics.html...")
            await page.goto(f"http://localhost:{PORT}/analytics.html")
            await page.wait_for_load_state("networkidle")
            await page.screenshot(
                path="../frontend_verification_analytics.png", full_page=True
            )
            print("Screenshot saved: frontend_verification_analytics.png")

        except Exception as e:
            print(f"Playwright error: {e}")
            raise

        await browser.close()


if __name__ == "__main__":
    # Start server in thread
    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()

    # Give server a moment to start (using async sleep in async main or just wait here)
    # Since this is the main entry point and we launch the async loop next,
    # blocking sleep here is acceptable as it happens before the loop starts.
    # However, to be fully async-compliant in spirit:
    import time

    time.sleep(2)

    try:
        asyncio.run(verify_ui_async())
    except Exception as e:
        print(f"UI verification failed: {e}")
        sys.exit(1)

    print("UI verification complete.")
