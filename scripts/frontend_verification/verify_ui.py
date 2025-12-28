import http.server
import os
import socketserver
import sys
import threading
import time

from playwright.sync_api import sync_playwright

# Serve the frontend directory
PORT = 8082
DIRECTORY = "frontend"


def serve():
    os.chdir(DIRECTORY)
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()


def verify_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # 1. Index Page
        print("Visiting index.html...")
        page.goto(f"http://localhost:{PORT}/index.html")
        page.wait_for_load_state("networkidle")

        page.screenshot(path="../frontend_verification_index_fa.png", full_page=True)
        print("Screenshot saved: frontend_verification_index_fa.png")

        # English Screenshot
        print("Switching to English for screenshot...")
        page.evaluate("document.documentElement.lang = 'en'")
        page.screenshot(path="../frontend_verification_index_en.png", full_page=True)

        # 2. Analytics Page
        print("Visiting analytics.html...")
        page.goto(f"http://localhost:{PORT}/analytics.html")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="../frontend_verification_analytics.png", full_page=True)
        print("Screenshot saved: frontend_verification_analytics.png")

        browser.close()


if __name__ == "__main__":
    # Start server in thread
    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()

    # Give server a moment to start
    time.sleep(2)

    try:
        verify_ui()
    except Exception as e:
        print(f"UI verification failed: {e}")
        sys.exit(1)

    print("UI verification complete.")
