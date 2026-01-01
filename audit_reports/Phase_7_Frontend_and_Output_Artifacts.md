# Phase 7: Frontend & Output Artifacts - Analysis Report (Deep Scan)

## 7. Overview
This phase analyzes how the system generates output artifacts (JSON configs, base64 subscriptions, etc.) and the structure of the frontend (HTML/JS/WASM).

## 7.1. Frontend Code (`frontend/assets/js/`)

### 7.1.1. `proxies.js`
**Analysis**:
*   **XSS Safety**:
    *   Uses `textContent` for dynamic text (e.g., pagination buttons).
    *   Uses `innerHTML` for SVG charts and icons. This is generally safe if the content is static or carefully constructed.
    *   **Risk**: `trendCell.innerHTML` constructs an SVG string. The values come from `validHistory` (numbers). Safe.
    *   **Risk**: `trendColor` is derived from comparison. Safe.
*   **Virtualization**: Does NOT use virtual scrolling. Renders `itemsPerPage` (default 50) rows. This is fine for moderate lists but might lag if user sets page size to 5000.
*   **Features**:
    *   Sparklines for latency trend (Nice UI touch).
    *   Pagination with Unicode arrows (‹, ›).
    *   Vector-based search (`calculateSimilarity` - not visible but referenced).

### 7.1.2. `stego.js`
**Analysis**:
*   **Key Injection**: `const SECRET_KEY = "PLACEHOLDER_KEY_INJECTED_BY_CI";`.
    *   **Critical**: The frontend logic *throws* if this key is not replaced. This confirms the requirement for a CI/CD build step to inject the key.
*   **Parsing**:
    *   Uses `fetch(imageUrl, { cache: "no-store" })`. Good for freshness.
    *   Uses `fernet` JS library (global).
    *   **Memory Safety**: `buffer` can be large (5MB image). `Uint8Array` slice creates copies? `slice()` on TypedArray creates a copy. `subarray()` creates a view. It uses `slice`. Optimization opportunity.
    *   **Payload Limit**: Checks `CS_CONSTANTS.STEGO_MAX_PAYLOAD_SIZE` (implied global) before decompression. Good security check (Zip bomb protection).

### 7.1.3. `washer_client.js`
**Analysis**:
*   **Stub**: Currently a mock ("Washer Client: Ready").
*   **Purpose**: Future feature to allow client-side washing (using WASM or API)?

## 7.2. Output Generation (`src/configstream/output.py`, `output_logic.py`)

### 7.2.1. Logic
**Analysis**:
*   `generate_categorized_outputs`:
    *   Calls `generate_smart_chains` (intelligence).
    *   Calls `generate_split_outputs` (converters).
    *   Generates Base64 Subscription (`sub.txt`).
    *   Generates Country/Protocol specific JSONs.
*   **Atomic Writes**: Uses `AtomicFileWriter.write_text` (likely write-temp-move pattern).

### 7.2.2. Metadata (`save_metadata`)
**Analysis**:
*   Aggregates stats from `PipelineStats` (or dict).
*   **Heuristics**: If stats are missing (e.g., from a merge script), it recalculates some counts by iterating `proxies`.
*   **Frontend Keys**:
    *   `sources_count`: "total configured sources".
    *   `vwarp_win_rate`, `smart_chain_count`.
    *   `latency_distribution`.

## 7.3. Converters (`src/configstream/converters/clash.py`)
**Analysis**:
*   **Coverage**: Support for `ss`, `vmess`, `trojan`, `vless`.
*   **Fallback**: If protocol unknown, returns `None`.
*   **Naming**: Uses `proxy.remarks` if valid, else generic name.
*   **Reality Support**: Supports `vless` Reality (`reality-opts`).
*   **Transport**: Mappings for `ws` (with headers) and `grpc` (service name).

## 7.4. Generators (`src/configstream/generators/split.py`)
**Analysis**:
*   **Tank (VPN)**: `singbox-vpn.json`. Uses `tun` inbound.
    *   `auto_route`: True. `strict_route`: True. This is a full VPN config.
    *   **Selectors**: "🌍 Proxy Select", "🚀 Auto", "🛡️ Washed".
*   **Sniper (Proxy)**: `singbox.json`. Uses `mixed` inbound (SOCKS/HTTP).
    *   **Fragmentation**: Injects `tls_fragment` into valid proxies. This is an anti-censorship feature (Client Hello Fragmentation).
    *   **Strip Metadata**: `_strip_internal_metadata` removes internal keys (`_process`) to prevent Sing-box parsing errors.
*   **Clash**: Calls `generate_clash_config`.

## Recommendations
1.  **Frontend Build**: Ensure the `sed` replacement for `SECRET_KEY` is robust (handles quotes, escapes).
2.  **JS Optimization**: Use `subarray` instead of `slice` in `stego.js` to avoid memory churn on mobile devices.
3.  **WASM**: Document how `wasm_exec.js` is kept in sync with the Go version used to build the binary.
