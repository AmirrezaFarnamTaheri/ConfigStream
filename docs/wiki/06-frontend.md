# 06. Frontend & User Experience

The ConfigStream frontend is a **Progressive Web App (PWA)** designed for speed, resilience, and visualization. It adheres to a "No Build Step" philosophy for the frontend code itself (Vanilla JS), though the backend generates the data it consumes.

## Architecture

*   **Framework**: Vanilla ES6+ JavaScript. No React, Vue, or Angular.
*   **Styling**: Custom CSS variables for theming.
*   **Data Source**: Static JSON files (`metadata.json`, `proxies.json`) fetched from the `output/` directory.

### The "Cache-First" Strategy (Service Worker)

We use a custom Service Worker (`service-worker.js`) to make the site censorship-resistant.

1.  **Assets (HTML/CSS/JS)**: Cached immediately on first load. The app works offline.
2.  **Data (JSON)**: Network-First. We try to fetch the latest proxy list. If the network fails (blocked), we serve the last cached list.
3.  **Updates**: The SW checks for a new version of the app in the background.

## Visualization Components

### 1. The Globe (`globe.gl`)
A WebGL-based 3D globe visualization.
*   **Data**: Latency distribution from `metadata.json`.
*   **Arcs**: Draws arcs from the user's estimated location to the proxy location.
*   **Color Coding**: Green (Fast), Yellow (Medium), Red (Slow).

### 2. Analytics (`Chart.js`)
*   **Protocol Distribution**: Doughnut chart.
*   **Country Distribution**: Bar chart.
*   **Latency Heatmap**: A scatter plot of Ping vs. Time.

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
*   **Process**:
    1.  Frontend tokenizes the query.
    2.  Fetches `vectors.json` (pre-computed).
    3.  Calculates **Cosine Similarity** between query vector and proxy vectors.
    4.  Ranks results.
*   **Performance**: Done in a Web Worker to avoid blocking the UI thread.

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
