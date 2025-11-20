import os
from playwright.sync_api import sync_playwright
import json

def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Mock data for analytics
        mock_data = {
            "last_updated_utc": "2023-01-01T12:00:00Z",
            "total_proxies": 100,
            "total_working": 50,
            "total_fetched": 200,
            "duration_seconds": 10.5,
            "protocols": {"vmess": 50, "vless": 50},
            "countries": {"US": 50, "DE": 50},
            "country_stats": {"US": 50, "DE": 50},
            "latency_distribution": {"fast": 10, "medium": 20, "slow": 10, "very_slow": 10},
            "protocol_colors": {"vmess": "#ff0000", "vless": "#00ff00"}
        }

        # Mock fetch
        mock_json = json.dumps(mock_data)
        page.add_init_script(f"""
            const originalFetch = window.fetch;
            window.fetch = async (url, options) => {{
                if (url.includes('api/stats') || url.includes('metadata.json')) {{
                    return {{
                        ok: true,
                        status: 200,
                        json: async () => ({mock_json})
                    }};
                }}
                if (url.includes('proxies.json')) {{
                    return {{
                        ok: true,
                        status: 200,
                        json: async () => ([])
                    }};
                }}
                return originalFetch(url, options);
            }};
        """)

        cwd = os.getcwd()

        # 1. Check Homepage
        print("Checking Homepage...")
        page.goto(f"file://{cwd}/frontend/index.html")
        page.wait_for_selector("h1")
        page.screenshot(path="verification/homepage.png")

        # 2. Check Analytics (Globe)
        print("Checking Analytics...")
        page.goto(f"file://{cwd}/frontend/analytics.html")
        page.wait_for_selector("#globe-viz canvas", state="attached", timeout=10000) # Wait for canvas
        # Wait a bit for globe to render
        page.wait_for_timeout(2000)
        page.screenshot(path="verification/analytics.png")

        # 3. Check Proxies (Search)
        print("Checking Proxies...")
        page.goto(f"file://{cwd}/frontend/proxies.html")
        page.wait_for_selector("#searchInput")
        page.fill("#searchInput", "fastest")
        page.screenshot(path="verification/proxies.png")

        browser.close()
        print("Verification complete.")

if __name__ == "__main__":
    verify_frontend()
