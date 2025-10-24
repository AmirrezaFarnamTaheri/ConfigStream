
import asyncio
from playwright.async_api import async_playwright
import http.server
import socketserver
import threading
import os

PORT = 8080
SCREENSHOT_DIR = "jules-scratch/verification"
PAGES = ["index.html", "proxies.html", "statistics.html"]

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=".", **kwargs)

def run_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()

async def main():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    await asyncio.sleep(2)  # Give server time to start

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        for page_name in PAGES:
            await page.goto(f"http://localhost:{PORT}/{page_name}")
            await page.wait_for_load_state('networkidle')
            screenshot_path = os.path.join(SCREENSHOT_DIR, page_name.replace('.html', '.png'))
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved to {screenshot_path}")
        await browser.close()

if __name__ == "__main__":
    # Stop the server by killing the process
    asyncio.run(main())
    print("Verification complete. Manually stop the server if it's still running.")
