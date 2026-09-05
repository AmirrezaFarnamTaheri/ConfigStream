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

### 1. No Raw Runtime `innerHTML`
*   **Never** assign variable, metadata, translation, subscription, or user-provided data to `innerHTML`.
*   **Use** `textContent`, `appendChild`, `replaceChildren`, and small DOM builders for text and UI updates.
*   **If rich markup is required**, sanitize it first and insert the returned DOM node or fragment. Do not pass sanitized strings back into a raw HTML sink.
*   Trusted internal HTML helpers must stay narrowly scoped to fixed project-owned strings and remain covered by frontend security tests.

### 2. DOMPurify
*   We load `DOMPurify` (vendored in `assets/libs/purify.min.js` and pinned in `assets/vendor-manifest.json` with version and SHA-256 provenance).
*   Ensure it is included in your HTML file before your scripts run.
*   Any large block of HTML constructed from data (e.g., Markdown rendering, Proxy Tables) must be passed through `DOMPurify.sanitize()` and inserted as a DOM node/fragment rather than assigned as raw markup.

### 3. URL Handling
*   Validate all URLs before setting them as `href` or `src`.
*   Use `validateURL()` helper from `utils.js`.
*   Avoid `javascript:` URIs.

### 4. Dependencies
*   **Vendor everything**. Do not rely on external CDNs (they can be blocked or compromised).
*   Keep `assets/libs/` clean. Only minimal, audited libraries.
*   Production pages load critical JS/CSS, globe textures, country flags, and Lab helper downloads from same-origin assets (`assets/libs/`, `assets/images/globe/`, `assets/images/flags/`, and `tools/`). Typography uses platform system stacks and does not ship or fetch font binaries. Remote URLs may exist only as user-initiated links or explicitly optional fallbacks, not as runtime dependencies.
*   Localized assets must preserve the online experience. If an exact local equivalent is not available, keep the original behavior in the online path and add a clearly separate offline fallback instead of silently downgrading the main UI.
*   Update `assets/vendor-manifest.json` whenever adding, refreshing, or replacing vendored runtime assets.

### 5. Content Security Policy (CSP)
*   Primary pages enforce a local-first CSP via meta tag.
*   Baseline policy: `default-src 'self'; script-src 'self' 'unsafe-inline' blob:; style-src 'self' 'unsafe-inline'; font-src 'none'; img-src 'self' data: blob:; connect-src 'self' ws: wss: data:; worker-src 'self' blob:; object-src 'self'; base-uri 'self'; form-action 'self';`
*   Do not add remote CDN hosts to CSP for production runtime assets.

## Visualization Components

### 1. The Globe (`globe.gl`)
A WebGL-based 3D globe visualization.
*   **Data**: Latency distribution from `metadata.json` (`latency_distribution`, `latency_by_country`, `latency_by_protocol`).
*   **Arcs**: Draws arcs from the user's estimated location to the proxy location.
*   **Color Coding**: Green (Fast), Yellow (Medium), Red (Slow).
*   **Target — Hardware Throttling (`IntersectionObserver`)**: Pause the animation loop when `#globe-viz` leaves the active viewport; verify the pause and resume in a browser test.
*   **Target — Layout Reserve**: Before canvas initialization, reserve an explicit `aspect-ratio: 16/9` box with a `min-height: 500px`; validate cumulative-layout-shift behavior in the visual suite.

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

## Chain Laboratory (`lab.html` + `assets/js/lab/` modules)

The Laboratory is a 5-step interactive chain builder that guides users from zero to a working proxy chain:

### Step 1: Parse Proxy
*   **Manual URI Paste**: User pastes a proxy URI (VLESS, VMess, Trojan, SS, Hysteria2, TUIC, WireGuard).
*   **Pre-Tested Proxies**: Users can click "Load Pre-Tested Proxies" to fetch the plaintext `proxies.txt` artifact from the deployed pipeline output. The verified URI list is parsed and displayed in a dropdown grouped by protocol.
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
*   For local verification when the pinned browser cannot be downloaded, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to an installed Chromium executable. Both Python and Node browser checks use that explicit path; it takes precedence over `PLAYWRIGHT_BROWSER_CHANNEL`. Readiness checks require the selected executable rather than an unrelated cached version, and launch failures fail the tests. CI continues to use its installed pinned browser by default.

## Cache Architecture

ConfigStream implements a context-aware caching system that optimizes performance while ensuring data freshness. Think of it as a "smart newspaper delivery" — you get yesterday's paper immediately while today's is being printed, and the system knows exactly when a new edition is available.

### Update Detection (`update-detector.js`)

The target `UpdateDetector` may poll with lightweight HTTP `HEAD` requests as
an optimization. A changed `Last-Modified` value is only a fetch hint; the
detector must then verify the manifest identity and signed metadata before
reporting an update. It must not treat publication time as data freshness.

### Multi-Layer Caching Strategy (`cache-config.js`)

| Strategy | Resources | Behavior |
|---|---|---|
| **cacheFirst** | CSS, JS, images, fonts, HTML | Serve from cache immediately; update in background |
| **networkFirst** | `metadata.json`, `proxies.json`, `base64.txt` | Try network; fall back to cache if offline |
| **Stale-While-Revalidate** | All dynamic data | Show cached data instantly, refresh in background |

### IndexedDB Storage (`cache-manager.js`)

Large datasets (the full proxy list can be 5,000+ items) are stored in **IndexedDB** rather than LocalStorage to avoid quota limits and main-thread blocking. The `IDBHelper` class wraps IndexedDB operations with Promises for clean async usage.

For proxy lists, cached records carry snapshot identity from `metadata.json` (`proxies_snapshot_hash` where available). When differential update mode is enabled, `CacheManager` probes the sibling metadata endpoint before serving a cached record and fetches fresh data if the published snapshot hash changed.

### Data Flow

```text
Page Load → Service Worker (Cache First for assets)
         → CacheManager checks IndexedDB for data
         → If fresh → Render immediately
         → If stale → Render cached, fetch fresh in background
         → UpdateDetector may issue a conditional metadata request as a cache hint
         → Candidate update → verify manifest identity, digest, signature, and signed metadata → Update IndexedDB → Dispatch event → Re-render UI
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

## Web Interface Standards & Interaction Craft

The following standards govern frontend rendering, WebGL performance, and motion hygiene (codified in [`DESIGN.md`](../../../DESIGN.md) and [`interface-design.md`](../../../interface-design.md)):

1. **Focus**: Every interactive control has an explicit `:focus-visible` ring (`2px solid #06b6d4`).
2. **Numeric stability**: Telemetry uses `font-variant-numeric: tabular-nums` across all tables, latencies, and ports.
3. **Motion**: Decorative animations use only `transform` and `opacity`.
4. **Reduced motion**: `@media (prefers-reduced-motion: reduce)` universally disables decorative loops and sets animation durations to `0.01ms`.
5. **Layout stability**: Chart canvases reserve `400px`; the globe reserves `500px` (`min-height`).
6. **WebGL & Animation Offscreen Gating (`/optimize-web-animations`)**:
   - **DPR Clamping**: Globe.gl pixel ratio is capped at `Math.min(window.devicePixelRatio || 1, 1.5)` to prevent GPU overdraw and memory pressure on high-DPI mobile screens.
   - **Offscreen Gating**: An `IntersectionObserver` on `#globe-viz` (threshold: `0.01`) toggles `data-animation-active` and pauses `requestAnimationFrame` / `controls.autoRotate` when the globe leaves the viewport, resuming smoothly on re-entry.
   - **Context Loss Recovery**: `webglcontextlost` cancels RAF and suspends render loops; `webglcontextrestored` rebuilds the scene graph without full page crash.
   - **Teardown Hooks**: `window._disposeGlobe()` disconnects observers, clears rotation timers, and disposes WebGL renderers during client navigation.
   - **CSS Animation Pauses**: Offscreen sections and elements matching `.is-offscreen` or `[data-animation-active="false"]` enforce `animation-play-state: paused !important`.

### Trust Bootstrap and Freshness Contract

Every public page that uses `verifier.js` or `artifact-state.js` must load its
scripts in this order: `runtime-config.js`, `constants.js`, `verifier.js`, then
`artifact-state.js`. The page-level test matrix must cover a missing,
malformed, and valid public key configuration. A public host must fail closed
on invalid trust configuration, while local development must retain its
explicitly scoped bypass.

| Surface | Required freshness source | Prohibited substitute | Required states |
|---|---|---|---|
| Home and download controls | Verified `metadata.last_updated_utc` | Browser wall clock | fresh, stale, invalid, error |
| Proxy catalog footer | Verified artifact timestamp | `new Date()` after fetch | fresh, stale, empty, error |
| Analytics | Verified artifact identity/version | per-visit timestamp cache buster | fresh, stale, invalid, error |
| Service worker shell | Artifact identity/commit-driven cache version | manually remembered cache bump | current shell, upgrade available, offline fallback |

The browser guard and release verifier treat a signed zero-working artifact as
an **empty, non-distributable** release: the catalog displays the empty state,
while copy and download controls remain disabled. It must never be presented as
fresh or as a cryptographic-tampering failure.

Update detection may use HTTP headers only as a cheap hint to perform a
verified fetch. It must not treat `Last-Modified`, a successful `HEAD`, or a
local fetch time as artifact freshness. Compare a verified manifest identity
and signed metadata generation timestamp before reporting an update.

### Performance Acceptance Targets

These are targets, not measurements. Test a production-sized fixture on a
throttled mobile profile: capture p95 input-to-render time for filtering,
repeat-view transfer behavior, long tasks during resize, and WebGL frame/heap
data. The proxy table must either preserve relevance ordering after filtering
or avoid relevance scoring entirely; it must not compute and then discard an
expensive relevance sort. Virtualization or worker search is justified only by
this measured fixture evidence.

## Related Documentation

*   **[Home Page](Home_Page.md)** — Dashboard components, globe, hero downloads.
*   **[Proxies Page](Proxies_Page.md)** — Data grid, filtering, WASM testing.
*   **[Analytics Page](Analytics_Page.md)** — Charts, evasion trends, data sources.
*   **[Sing-box Configuration Guide](../encyclopedia/tools/singbox_configuration_guide.md)** — How the Lab's exported configs are structured.
*   **[Networking Terms — WebSocket](../encyclopedia/glossary/networking_terms.md)** — WS transport used by WASM tester.
*   **[WARP & Clean IPs](../encyclopedia/networking/warp.md)** — How the Lab discovers and uses clean IPs.
