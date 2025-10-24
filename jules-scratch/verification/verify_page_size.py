
import asyncio
from playwright.async_api import async_playwright
import http.server
import socketserver
import threading
import os
import time

PORT = 8000
httpd = None
server_thread = None

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='.', **kwargs)

def run_server():
    global httpd
    # This context manager will handle closing the socket
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()

def start_server():
    global server_thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    time.sleep(2) # Give server time to start

def stop_server():
    global httpd, server_thread
    if httpd:
        print("Shutting down server...")
        httpd.shutdown()
        httpd.server_close()
        httpd = None
    if server_thread:
        print("Joining server thread...")
        server_thread.join(timeout=5)
        if server_thread.is_alive():
            print("Server thread did not join.")
        else:
            print("Server thread joined.")
        server_thread = None


async def main():
    start_server()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(f"http://localhost:{PORT}/proxies.html")
                await page.wait_for_selector('#proxiesTableBody tr', timeout=20000)

                await page.screenshot(path="jules-scratch/verification/verification_default_50.png")

                await page.select_option('select#pageSize', '25')
                await page.wait_for_selector('#proxiesTableBody tr', timeout=20000)
                await asyncio.sleep(2)
                await page.screenshot(path="jules-scratch/verification/verification_25.png")

                await page.select_option('select#pageSize', '100')
                await page.wait_for_selector('#proxiesTableBody tr', timeout=20000)
                await asyncio.sleep(2)
                await page.screenshot(path="jules-scratch/verification/verification_100.png")

            except Exception as e:
                print(f"An error occurred during Playwright execution: {e}")
            finally:
                await browser.close()
    finally:
        stop_server()

if __name__ == "__main__":
    # Added a loop to ensure the port is free before starting
    for i in range(5):
        try:
            asyncio.run(main())
            break
        except OSError as e:
            if "Address already in use" in str(e) and i < 4:
                print(f"Port {PORT} is busy. Retrying in 5 seconds...")
                time.sleep(5)
            else:
                raise
