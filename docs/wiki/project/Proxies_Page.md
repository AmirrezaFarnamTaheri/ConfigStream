# Proxies Page Documentation

The **Proxies** page is the "Search Engine" of ConfigStream. It provides a granular, searchable, and filterable list of every single valid proxy in the current batch.

## Design Philosophy: "Power to the User"

While the Home page offers "The Tank" (one-click bundles), the Proxies page is for power users who want to hand-pick specific nodes—perhaps a low-latency server in Japan for gaming, or a residential IP in the US for streaming.

### Features

#### 1. The Data Grid
*   **Columns**:
    *   **Type**: Protocol icon (VLESS, VMess, etc.).
    *   **Location**: Country flag + Country Name + City.
    *   **ISP**: The hosting organization (e.g., Amazon, Google, Oracle).
    *   **Latency**: Color-coded numerical value (ms).
    *   **Score**: The internal reliability score (0-100).
    *   **Action**: "Copy" button.

#### 2. Advanced Filtering
*   **Search Bar**: Full-text search across IP, City, ISP, and Name.
*   **Protocol Filter**: Checkboxes to show/hide specific protocols.
*   **Country Filter**: Dropdown to select specific regions.
*   **Sort**: Options to sort by Latency (Asc/Desc), Score, or Country.

#### 3. Export Tools
*   **"Copy All"**: Copies the currently filtered list to the clipboard.
*   **"Download Filtered"**: Generates a `.json` or `.txt` file of the current view.
*   **QR Code**: Generates a QR code for the selected proxy for easy mobile scanning.

#### 4. Verification Status
*   Each row displays the "Last Verified" timestamp.
*   **WASM Integration**: Users can click a "Test" button to verify the proxy *from their own browser* using the embedded `sing-box` WASM module, getting a real-time latency check that reflects their actual ISP conditions, not the GitHub Runner's.

#### 5. Sparkline History
Each proxy row includes a tiny inline chart (sparkline) showing the proxy's latency over the last 7 days. This gives users an instant visual indicator of stability — a flat line means consistent performance, while spikes indicate intermittent issues.

#### 6. Tag Badges
Proxies display colored badges for their tags:
*   **Protocol**: `VLESS`, `Trojan`, `VMess`, etc.
*   **Process**: `NATIVE`, `WASHED`, `REVIVED`, `CHAIN`, `SHIELDED`.
*   **Evasion**: `UTLS`, `FRAG`, `MUX`, `ALPN`.
*   **DNS**: `DNS-SAFE`, `DNS-HARDENED`.

## Technical Implementation

*   **Data Source**: `proxies.json` fetched via `fetchProxies()` in `utils/network.js`. Falls back to `/api/proxies`.
*   **Virtual Scrolling**: Only renders visible rows (typically 20-50 at a time) regardless of total dataset size. Handles 5,000+ items without DOM bloat.
*   **Search Logic**: Pure JavaScript `String.includes()` filtering across all text fields. Debounced at 200ms to avoid excessive re-renders.
*   **Clipboard API**: Uses `navigator.clipboard.writeText()` for one-click URI copying. Falls back to `document.execCommand('copy')` on older browsers.
*   **QR Generation**: Client-side QR code rendering using a vendored library (no external CDN dependency).
*   **Responsiveness**: Table columns collapse on mobile — ISP and Score columns are hidden, leaving Type, Location, Latency, and Action visible.
