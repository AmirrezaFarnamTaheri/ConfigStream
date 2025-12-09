from playwright.sync_api import sync_playwright
import os
import sys
import threading
import http.server
import socketserver
import time

# Serve the frontend directory
PORT = 8081  # Use a different port to avoid conflict if both run? Or same.
DIRECTORY = "frontend"


def serve():
    os.chdir(DIRECTORY)
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()


def verify_structure():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # 1. Index Page
        print("Visiting index.html...")
        page.goto(f"http://localhost:{PORT}/index.html")
        page.wait_for_load_state("networkidle")

        # Check title
        print(f"Page title: {page.title()}")

        # Force Farsi and check font
        print("Switching language to Farsi...")
        page.evaluate("document.documentElement.lang = 'fa'")
        # Inject test element to check font
        font_family = page.evaluate("getComputedStyle(document.body).fontFamily")
        print(f"Computed Body Font Family (FA): {font_family}")

        if "Mikhak" in font_family or "Vazirmatn" in font_family:
            print("SUCCESS: Farsi font stack applied.")
        else:
            print(f"WARNING: Farsi font stack might be missing. Got: {font_family}")

        # English
        print("Switching language to English...")
        page.evaluate("document.documentElement.lang = 'en'")
        font_family_en = page.evaluate("getComputedStyle(document.body).fontFamily")
        print(f"Computed Body Font Family (EN): {font_family_en}")

        browser.close()


if __name__ == "__main__":
    # Start server in thread
    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()

    # Give server a moment to start
    time.sleep(2)

    try:
        verify_structure()
    except Exception as e:
        print(f"Structure verification failed: {e}")
        sys.exit(1)

    print("Structure verification complete.")
