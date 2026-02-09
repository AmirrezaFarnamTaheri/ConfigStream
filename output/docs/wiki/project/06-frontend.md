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
*   We load `DOMPurify` (vendored in `assets/js/lib/purify.min.js`).
*   Ensure it is included in your HTML file before your scripts run.
*   Any large block of HTML constructed from data (e.g., Markdown rendering, Proxy Tables) must be passed through `DOMPurify.sanitize()`.

### 3. URL Handling
*   Validate all URLs before setting them as `href` or `src`.
*   Use `validateURL()` helper from `utils.js`.
*   Avoid `javascript:` URIs.

### 4. Dependencies
*   **Vendor everything**. Do not rely on external CDNs (they can be blocked or compromised).
*   Keep `assets/js/lib/` clean. Only minimal, audited libraries.

### 5. Content Security Policy (CSP)
*   The `index.html` should enforce a strict CSP (via meta tag or headers).
*   `script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:;` (Adjusted for WASM/Inline scripts requirements, tighten where possible).

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
*   **Planned Enhancements (Not Yet Implemented)**:
    *   Replace the heuristic score with a proper vector‑space similarity measure (for example, cosine similarity over dense vectors).
    *   Move heavy ranking into a Web Worker to avoid blocking the UI thread for very large datasets.

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

### Step 3: Build Chain (6 Strategies)
1.  **WARP Tunnel**: Standard shielding through Cloudflare WARP.
2.  **Double WARP**: Two layers of WireGuard encryption.
3.  **Relay Chain (Multi-Hop)**: Up to 4 intermediate hops of any protocol (SOCKS5, HTTP, VLESS, VMess, Trojan, SS, WARP). Replaces the old "Proxy Cascade" and "Intranet Relay" — a relay is any intermediate proxy, not limited to LAN. Each layer has a pipeline proxy picker.
4.  **TLS Fragment**: Split TLS handshake to evade stateless DPI.
5.  **CDN Worker**: Route through a user-deployed Cloudflare Worker.
6.  **Custom JSON**: Paste raw sing-box outbound JSON for advanced users.

Each strategy has its own options panel. Advanced evasion options (uTLS fingerprint, ALPN, multiplexing, padding) are available as a collapsible section.

### Export Formats & Core Compatibility
All chain configs are exported in formats compatible with the three major proxy cores:
*   **Sing-box JSON**: Uses `detour` field for chaining (primary format).
*   **Xray/V2Ray JSON**: Uses `proxySettings.tag` for chaining. Note: WireGuard outbounds are not natively supported by Xray.
*   **Clash/Mihomo YAML**: Uses `dialer-proxy` for chaining.

### Step 4: Test Chain
*   **Live API Test**: Sends the chain config to a test endpoint.
*   **Manual Fallback**: Provides `sing-box run -c` commands for local testing.

### Step 5: Export
*   **Formats**: Sing-box JSON, Clash YAML, Xray JSON, Nekobox link, raw URI, QR code, Python script, Bash script.
*   **File Download**: One-click download of the generated config.
*   **Import Guide**: Step-by-step instructions for Hiddify, Clash Verge, V2RayN, V2RayNG, Nekobox.

### Offline Tools
*   **`lab-scanner.py`**: Zero-dependency Python scanner with 7+ scan phases, interactive chain builder, and 6-strategy auto-chain detection.
*   **`lab-runner.sh`**: Bash script that auto-downloads sing-box and runs chain configs.
*   **`lab-offline.html`**: Self-contained HTML chain builder that works without a server.

## Internationalization (i18n)

We support RTL (Right-to-Left) languages natively for our Persian and Arabic users.
*   **Dictionary**: `assets/js/i18n.js` contains mappings.
*   **Detection**: Auto-detects browser language.
*   **Switching**: Dynamic, no reload required.
