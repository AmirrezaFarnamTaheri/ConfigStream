# 06. Frontend & User Experience

The ConfigStream frontend is a **Progressive Web App (PWA)** designed for speed, resilience, and visualization. It adheres to a "No Build Step" philosophy for the frontend code itself (Vanilla JS), though the backend generates the data it consumes.

## Architecture

*   **Framework**: Vanilla ES6+ JavaScript. No React, Vue, or Angular.
*   **Styling**: Custom CSS variables for theming.
*   **Data Source**: Static JSON files (`metadata.json`, `proxies.json`, `revived.json`, `singbox-chains.json`) fetched from the `output/` directory.

### The "Cache-First" Strategy (Service Worker)

We use a custom Service Worker (`service-worker.js`) to make the site censorship-resistant.

1.  **Assets (HTML/CSS/JS)**: Cached immediately on first load. The app works offline.
2.  **Data (JSON)**: Network-First. We try to fetch the latest proxy list. If the network fails (blocked), we serve the last cached list.
3.  **Updates**: The SW checks for a new version of the app in the background.

## Security Hardening Checklist

When making changes to the frontend, you **must** adhere to these security practices to prevent XSS (Cross-Site Scripting) and other client-side attacks.

### 1. No Unsafe `innerHTML`
*   **Never** assign user-controlled data directly to `innerHTML`.
*   **Use** `textContent` for text updates.
*   **Use** `updateElement(selector, content, { method: 'textContent' })` helper.
*   **If you MUST use HTML**:
    *   Sanitize it first using `DOMPurify.sanitize()`.
    *   Use `updateElement(selector, content, { method: 'innerHTML' })`, which handles sanitization automatically (unless `trustedHTML: true` is set).

### 2. DOMPurify
*   We load `DOMPurify` (vendored in `assets/libs/purify.min.js`).
*   Ensure it is included in your HTML file before your scripts run.
*   Any large block of HTML constructed from data (e.g., Markdown rendering, Proxy Tables) must be passed through `DOMPurify.sanitize()`.

### 3. URL Handling
*   Validate all URLs before setting them as `href` or `src`.
*   Use `validateURL()` helper from `utils.js`.
*   Avoid `javascript:` URIs.

### 4. Dependencies
*   **Vendor everything**. Do not rely on external CDNs (they can be blocked or compromised).
*   Keep `assets/libs/` clean. Only minimal, audited libraries.
*   Production pages load critical JS/CSS, fonts, globe textures, country flags, and Lab helper downloads from same-origin assets (`assets/libs/`, `assets/fonts/`, `assets/images/globe/`, `assets/images/flags/`, and `tools/`). Remote URLs may exist only as user-initiated links or explicitly optional fallbacks, not as runtime dependencies.
*   Localized assets must preserve the online experience. If an exact local equivalent is not available, keep the original behavior in the online path and add a clearly separate offline fallback instead of silently downgrading the main UI.
*   Update `assets/vendor-manifest.json` whenever adding, refreshing, or replacing vendored runtime assets.

### 5. Content Security Policy (CSP)
*   Primary pages enforce a local-first CSP via meta tag.
*   Baseline policy: `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: blob:; connect-src 'self' ws: wss: data:; worker-src 'self' blob:; object-src 'self'; base-uri 'self'; form-action 'self';`
*   Do not add remote CDN hosts to CSP for production runtime assets.

## Visualization Components

### 1. The Globe (`globe.gl`)
A WebGL-based 3D globe visualization.
*   **Data**: Latency distribution from `metadata.json` (`latency_distribution`, `latency_by_country`, `latency_by_protocol`).
*   **Arcs**: Draws arcs from the user's estimated location to the proxy location.
*   **Color Coding**: Green (Fast), Yellow (Medium), Red (Slow).

### 2. Analytics (`Chart.js`)
*   **Protocol Distribution**: Doughnut chart (`protocols`).
*   **Country Distribution**: Bar chart (`country_stats`).
*   **Latency Heatmap**: Average latency per country (`latency_by_country`).

### 3. Virtual Scrolling (The Proxy Table)
Rendering 5,000 DOM elements (table rows) kills the browser.
*   **Solution**: We implement **Virtual Scrolling**.
*   **Mechanism**: We only render the ~20 rows currently visible in the viewport. As the user scrolls, we dynamically recycle and update these DOM nodes.
*   **Result**: 60fps scrolling even with 100,000 proxies.

## WASM Edge Testing

This is the "Hero" feature. We allow users to verify proxies *from their own network*.

### The Bridge (`wasm_loader.js`)
1.  **Load**: Fetches `tester.wasm` (compiled from Go).
2.  **Instantiate**: Loads the WASM module into memory.
3.  **Expose**: Maps Go functions (e.g., `TestProxy`) to JavaScript functions (`window.testProxy`).

### The Challenge: Browser Sandbox
Browsers cannot open TCP sockets.
*   **WebSocket Proxies**: The WASM module uses the browser's `WebSocket` API to test `vmess+ws`, `vless+ws`, etc. These tests are **Real**.
*   **TCP Proxies**: The WASM module currently simulates a check or uses a fallback HTTP ping (if CORS allows).
*   **Future**: We are exploring WebTransport and Relay nodes.

## Vector Search (Natural Language)

*   **Input**: "Fast reliable US proxy"
*   **Process (Current Implementation)**:
    1.  Frontend tokenizes the query into lowercase keywords.
    2.  Fetches `vectors.json` (pre-computed) and proxy metadata.
    3.  Computes a simple keyword‑based relevance score on the client (protocol, country code, city, tags).
    4.  Ranks results by this score.
*   **Future**: Cosine similarity over dense vectors in a Web Worker for semantic search on large datasets.

## Time-Travel Sparklines

In the proxy table, the "Latency" column is not just a number. It is a story.
*   **Data**: `history: [100, 120, 900, 110, 115]`
*   **Visual**: A tiny SVG sparkline.
*   **Insight**: A user sees a spike (900ms) and knows the proxy is unstable, even if it says "115ms" right now.

## Chain Laboratory (`lab.html` + `lab.js`)

The Laboratory is a 5-step interactive chain builder that guides users from zero to a working proxy chain:

### Step 1: Parse Proxy
*   **Manual URI Paste**: User pastes a proxy URI (VLESS, VMess, Trojan, SS, Hysteria2, TUIC, WireGuard).
*   **Pre-Tested Proxies**: Users can click "Load Pre-Tested Proxies" to fetch working proxies from ConfigStream's pipeline output (`output/base64.txt`). Proxies are decoded from Base64, parsed, and displayed in a dropdown grouped by protocol.
*   **Subscription Load**: Or load from the existing subscription endpoint.
*   **Network Diagnosis**: An expandable section runs browser-based connectivity checks against 6 endpoints (Cloudflare, Google, GitHub, Wikipedia, DoH) and renders a censorship severity gauge with multi-strategy advice.
*   **Local Proxy Detection**: Users can specify an existing local proxy (Psiphon, V2RayN, Clash) as Layer 1.

### Step 2: Discover Clean IPs
*   **Auto Scan**: Probes ConfigStream's default clean Cloudflare IPs with latency measurement.
*   **Manual Entry**: Users can paste their own `IP:port` list.
*   **Local Scan**: Runs a browser-based scan of known Cloudflare endpoints.

### Step 3: Build Chain (9 Strategies)
1.  **WARP Tunnel**: Standard shielding through Cloudflare WARP.
2.  **Vwarp MASQUE**: Standard WARP chain plus Vwarp MASQUE metadata and CLI hint for deployments that use Vwarp's MASQUE/noize presets.
3.  **Vwarp AtomicNoize**: Standard WARP chain plus AtomicNoize metadata and CLI hint for fragmentation-style evasion outside native sing-box output.
4.  **Double WARP**: Two layers of WireGuard encryption.
5.  **WARP + Psiphon**: Standard WARP chain with Vwarp Psiphon metadata and country hint.
6.  **Relay Chain (Multi-Hop)**: Up to 4 intermediate hops of any protocol (SOCKS5, HTTP, VLESS, VMess, Trojan, SS, WARP). Replaces the old "Proxy Cascade" and "Intranet Relay" — a relay is any intermediate proxy, not limited to LAN. Each layer has a pipeline proxy picker.
7.  **TLS Fragment**: Legacy/manual recipe only. Native sing-box `tls_fragment` output is disabled; use Vwarp AtomicNoize for fragmentation-based evasion.
8.  **CDN Worker**: Route through a user-deployed Cloudflare Worker.
9.  **Custom JSON**: Paste raw sing-box outbound JSON for advanced users.

Each strategy has its own options panel. Advanced evasion options (uTLS fingerprint, ALPN, multiplexing, padding) are available as a collapsible section.

### Export Formats & Core Compatibility
All chain configs are exported in formats compatible with the three major proxy cores:
*   **Sing-box JSON**: Uses `detour` field for chaining (primary format).
*   **Xray/V2Ray JSON**: Uses `proxySettings.tag` for chaining. Xray-core supports WireGuard natively (`secretKey` + `peers[]` format).
*   **Clash/Mihomo YAML**: Uses `dialer-proxy` for chaining.

### Step 4: Test Chain
*   **Visible Mode State**: The Lab shows whether it is in live-test mode or manual-test mode before the user runs a check.
*   **Live API Test**: On backend-capable hosting, sends the chain config to a test endpoint.
*   **Manual Fallback**: On static hosting such as GitHub Pages, labels the page as manual-test mode and provides `sing-box run -c` commands for local testing.

### Step 5: Export
*   **Formats**: Sing-box JSON, Clash YAML, Xray JSON, Nekobox link, raw URI, offline QR payload, Python script, Bash script.
*   **File Download**: One-click download of the generated config.
*   **Import Guide**: Step-by-step instructions for Hiddify, Clash Verge, V2RayN, V2RayNG, Nekobox.

### Offline Tools
*   **`tools/lab-scanner.py`**: Zero-dependency Python scanner with 7+ scan phases, interactive chain builder, and 6-strategy auto-chain detection. GitHub Pages deploy copies it to `output/tools/lab-scanner.py`.
*   **`tools/lab-runner.sh`**: Bash script that auto-downloads sing-box and runs chain configs. GitHub Pages deploy copies it to `output/tools/lab-runner.sh`.
*   **`frontend/lab-offline.html`**: Self-contained HTML chain builder that works without a server.

## Regression Coverage

*   `tests/unit/test_frontend_local_first.py` blocks reintroducing runtime CDN hosts in primary frontend sources and verifies required vendored assets exist.
*   `tests/e2e/test_frontend.py::test_frontend_pages_load_with_external_network_blocked` loads primary pages while aborting every non-same-origin browser request.
*   `npm run test:frontend:no-network` runs the same same-origin-only browser smoke through Node Playwright for environments where the Python browser bundle is unavailable.
*   `npm run test:frontend:degraded` loads the same primary pages with JavaScript disabled, while still blocking non-same-origin requests.
*   `python scripts/run_test_profile.py frontend-browser` sets `CONFIGSTREAM_REQUIRE_PLAYWRIGHT=1`; missing Python Playwright browsers are a hard failure in that profile and in CI.

## Cache Architecture

ConfigStream implements a context-aware caching system that optimizes performance while ensuring data freshness. Think of it as a "smart newspaper delivery" — you get yesterday's paper immediately while today's is being printed, and the system knows exactly when a new edition is available.

### Update Detection (`update-detector.js`)

The `UpdateDetector` polls every 4 minutes using lightweight HTTP `HEAD` requests. When it detects a change in `Last-Modified` headers or `last_updated_utc` timestamps, it triggers selective fetches — only downloading the resources that actually changed, not the entire dataset.

### Multi-Layer Caching Strategy (`cache-config.js`)

| Strategy | Resources | Behavior |
|---|---|---|
| **cacheFirst** | CSS, JS, images, fonts, HTML | Serve from cache immediately; update in background |
| **networkFirst** | `metadata.json`, `proxies.json`, `base64.txt` | Try network; fall back to cache if offline |
| **Stale-While-Revalidate** | All dynamic data | Show cached data instantly, refresh in background |

### IndexedDB Storage (`cache-manager.js`)

Large datasets (the full proxy list can be 5,000+ items) are stored in **IndexedDB** rather than LocalStorage to avoid quota limits and main-thread blocking. The `IDBHelper` class wraps IndexedDB operations with Promises for clean async usage.

### Data Flow

```
Page Load → Service Worker (Cache First for assets)
         → CacheManager checks IndexedDB for data
         → If fresh → Render immediately
         → If stale → Render cached, fetch fresh in background
         → UpdateDetector starts polling (every 4 min)
         → On change → Selective fetch → Update IndexedDB → Dispatch event → Re-render UI
```

### Cache Troubleshooting
*   **Data not updating?** Check if `metadata.json` timestamp is current on the server. Hard refresh (Ctrl+F5) bypasses the Service Worker.
*   **Cache too aggressive?** Increment `VERSION` in `cache-config.js` to force a full cache reset.

> **See also**: [Security Concepts — Circuit Breaker](../encyclopedia/glossary/security_concepts.md) for the fail-open pattern used when cache checks fail.

## Internationalization (i18n)

We support RTL (Right-to-Left) languages natively for our Persian and Arabic users.
*   **Dictionary**: `assets/js/i18n.js` contains mappings.
*   **Detection**: Auto-detects browser language.
*   **Switching**: Dynamic, no reload required.

## Related Documentation

*   **[Home Page](Home_Page.md)** — Dashboard components, globe, hero downloads.
*   **[Proxies Page](Proxies_Page.md)** — Data grid, filtering, WASM testing.
*   **[Analytics Page](Analytics_Page.md)** — Charts, evasion trends, data sources.
*   **[Sing-box Configuration Guide](../encyclopedia/tools/singbox_configuration_guide.md)** — How the Lab's exported configs are structured.
*   **[Networking Terms — WebSocket](../encyclopedia/glossary/networking_terms.md)** — WS transport used by WASM tester.
*   **[WARP & Clean IPs](../encyclopedia/networking/warp.md)** — How the Lab discovers and uses clean IPs.
