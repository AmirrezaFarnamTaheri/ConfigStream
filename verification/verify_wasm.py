from playwright.sync_api import sync_playwright, expect
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Read the real JS file content
        with open("frontend/assets/js/proxies.js", "r") as f:
            js_content = f.read()

        # Create the HTML file injecting the JS
        with open("verification/test.html", "w") as f:
            f.write(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Test Proxy Table</title>
                <style>
                    /* Minimal CSS to make it look decent */
                    .hidden {{ display: none; }}
                    table {{ width: 100%; border-collapse: collapse; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; }}
                    .sparkline {{ border: 1px solid #eee; }}
                    .shield-badge {{ color: green; }}
                    .status-online {{ color: green; }}
                </style>
            </head>
            <body>
                <input id="searchInput" placeholder="Search...">
                <select id="filterProtocol"><option value="">All</option></select>
                <select id="filterCountry"><option value="">All</option></select>
                <select id="filterCity"><option value="">All</option></select>
                <span id="filterCount"></span>
                <button id="testWasm">Test WASM</button>

                <div id="loadingContainer" class="hidden">Loading...</div>
                <div id="emptyState" class="hidden">No proxies found</div>

                <table id="proxiesTable">
                    <thead>
                        <tr>
                            <th data-sort="protocol">Protocol</th>
                            <th data-sort="location">Location</th>
                            <th data-sort="latency">Latency</th>
                            <th data-sort="status">Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody id="proxiesTableBody"></tbody>
                </table>
                <div id="pagination-container"></div>

                <!-- Mock API -->
                <script>
                    window.api = {{
                        fetchProxies: async () => {{
                            return [
                                {{
                                    "id": "1",
                                    "protocol": "vmess",
                                    "country_code": "US",
                                    "city": "New York",
                                    "latency": 120,
                                    "is_working": true,
                                    "config": "vmess://...",
                                    "history": [100, 110, 800, 120, 115],
                                    "tags": ["washed"]
                                }},
                                {{
                                    "id": "2",
                                    "protocol": "ss",
                                    "country_code": "DE",
                                    "city": "Frankfurt",
                                    "latency": 50,
                                    "is_working": true,
                                    "config": "ss://...",
                                    "history": [40, 45, 50, 50, 48],
                                    "tags": []
                                }}
                            ];
                        }}
                    }};
                    // Mock WASM
                    window.checkProxy = async (config) => {{
                        return {{ success: true, latency: 99, message: "WASM Mock" }};
                    }};
                </script>

                <!-- Inject Real JS -->
                <script>
                {js_content}
                </script>
            </body>
            </html>
            """)

        cwd = os.getcwd()
        page_path = f"file://{cwd}/verification/test.html"

        page.goto(page_path)

        # Wait for table to populate
        page.wait_for_selector(".proxy-row")

        # 1. Verify Rows
        rows = page.locator(".proxy-row")
        expect(rows).to_have_count(2)

        # 2. Verify Sparkline
        sparkline = rows.first.locator("svg.sparkline")
        expect(sparkline).to_be_visible()

        # 3. Verify Washed Badge
        badge = rows.first.locator(".shield-badge")
        expect(badge).to_be_visible()

        # 4. Verify WASM Button exists
        wasm_btn = page.locator("#testWasm")
        expect(wasm_btn).to_be_visible()

        # Take Screenshot
        page.screenshot(path="verification/frontend_verify.png")
        print("Verification successful, screenshot saved.")

        browser.close()

if __name__ == "__main__":
    run()
