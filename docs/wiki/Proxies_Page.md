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

## Technical Implementation

*   **Data Source**: `proxies.json` (The full dataset).
*   **Pagination**: Implements client-side pagination or "Virtual Scrolling" (via `VirtualScroller` or similar) to handle lists of 5,000+ items without lagging the browser.
*   **Search Logic**: Pure JavaScript filtering.
*   **Clipboard API**: Uses `navigator.clipboard.writeText()` for one-click copying.
