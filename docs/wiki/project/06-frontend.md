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

## Internationalization (i18n)

We support RTL (Right-to-Left) languages natively for our Persian and Arabic users.
*   **Dictionary**: `assets/js/i18n.js` contains mappings.
*   **Detection**: Auto-detects browser language.
*   **Switching**: Dynamic, no reload required.
