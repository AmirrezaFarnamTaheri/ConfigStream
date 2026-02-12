# Home Page Documentation

The **Home** page is the primary entry point for the ConfigStream user interface. It is designed to provide immediate situational awareness of the proxy network's status and give users quick access to the most vital configurations.

## Design Philosophy: "At a Glance"

The Home page follows the "Dashboard" design pattern. It avoids overwhelming the user with lists of thousands of proxies. Instead, it aggregates data into high-level metrics and "Hero" download cards.

### Key Components

#### 1. Global Status Header
*   **Last Updated**: Displays the exact time the pipeline last successfully ran (converted to the user's local timezone). This builds trust by showing data freshness.
*   **Total Active Proxies**: The aggregate count of working proxies available for download.
*   **Success Rate**: A percentage metric indicating the health of the source ecosystem.

#### 2. The "Hero" Downloads
Three primary "Action Cards" dominate the view, tailored for the most popular use cases:

*   **The Tank (VPN Mode)**
    *   *File*: `singbox-vpn.json`
    *   *Purpose*: Full-device VPN tunneling. Best for users who want "set and forget" protection for all apps.
    *   *Engine*: Sing-box (Tun Mode).

*   **The Sniper (Routing Mode)**
    *   *File*: `singbox.json`
    *   *Purpose*: Selective routing. Uses Geosite/GeoIP rules to route only blocked traffic through proxies while keeping local traffic direct. Optimized for speed and battery life.
    *   *Engine*: Sing-box (Rule Mode).

*   **Universal Subscription**
    *   *File*: `base64.txt` (or `proxies.json` for structured data)
    *   *Purpose*: Compatibility. Base64 subscriptions work in most clients (v2rayN, Shadowrocket, etc.). `proxies.json` is intended for developers and analytics.

*   **Smart Chains**
    *   *File*: `singbox-chains.json`
    *   *Purpose*: Prebuilt chain outbounds (revived + smart chains) for advanced routing and DPI-resistant paths.

*   **Revived Proxies (JSON)**
    *   *File*: `revived.json`
    *   *Purpose*: Revived-only dataset for diagnostics and chaining workflows.

*   **Full Dataset (JSON)**
    *   *File*: `proxies.json`
    *   *Purpose*: Full structured dataset for developers and analytics.

#### 3. 3D Visualization (The Globe)
*   **Technology**: `globe.gl` (WebGL).
*   **Function**: Visualizes the physical location of proxy nodes.
*   **Interactivity**: Users can rotate the globe. Active nodes appear as pillars of light, with color intensity representing latency (Green = Fast, Red = Slow).
*   **Why**: It provides a visceral representation of the "Global Network" concept, reinforcing the idea that ConfigStream connects you to the world.

#### 4. Quick Analytics
A condensed version of the Analytics page, showing:
*   **Protocol Distribution**: A doughnut chart showing the mix of protocols (e.g., 40% VLESS, 30% VMess, 20% Trojan).
*   **Top Countries**: A bar chart listing the top 5 countries by proxy count.

#### 5. Download Dropdown
A secondary download section with a dropdown selector for all output formats:
*   **Sing-box (JSON)** / **Sing-box VPN** — Primary configs.
*   **Clash (YAML)** — For Clash Meta / Clash Verge users.
*   **Base64 / Plain Text** — Universal subscription formats.
*   **Shadowrocket / Surge / Quantumult X / Loon** — iOS/macOS client-specific formats.
*   **Smart Chains / Revived / Full Dataset** — Advanced outputs.

Each format supports three DNS profiles (Standard, DNS-Safe, DNS-Hardened) and three evasion modes (Standard, Stealth, Aggressive), selectable via dropdown controls.

#### 6. Evasion & DNS Controls
*   **DNS Profile Selector**: Standard / DNS-Safe (IP-only) / DNS-Hardened (DoH/DoT/DoQ).
*   **Evasion Mode Selector**: Standard / Stealth / Aggressive.
*   These controls dynamically update the download URLs to serve the appropriate file variant.

## Technical Implementation

*   **Data Source**: Fetches `metadata.json` via `fetchMetadata()` in `utils/network.js`. Falls back to `/api/stats` if primary URL fails.
*   **Rendering**: Vanilla JavaScript with direct DOM manipulation. No framework overhead.
*   **Globe**: `globe.gl` (Three.js/WebGL). Lazy-loaded, auto-rotates, pauses on user interaction, resumes after 2s idle. Falls back gracefully if WebGL is unavailable.
*   **Performance**: Globe is paused when not in viewport. Stat cards use `requestAnimationFrame` for smooth counter animations.
*   **Responsiveness**: Fully responsive layout. Globe hidden on small screens to save bandwidth and GPU.
