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
    *   *File*: `proxies.json` (or Base64 export)
    *   *Purpose*: Compatibility. A standard list format that can be imported into almost any client (v2rayN, Shadowrocket, etc.).

#### 3. 3D Visualization (The Globe)
*   **Technology**: `globe.gl` (WebGL).
*   **Function**: Visualizes the physical location of proxy nodes.
*   **Interactivity**: Users can rotate the globe. Active nodes appear as pillars of light, with color intensity representing latency (Green = Fast, Red = Slow).
*   **Why**: It provides a visceral representation of the "Global Network" concept, reinforcing the idea that ConfigStream connects you to the world.

#### 4. Quick Analytics
A condensed version of the Analytics page, showing:
*   **Protocol Distribution**: A doughnut chart showing the mix of protocols (e.g., 40% VLESS, 30% VMess, 20% Trojan).
*   **Top Countries**: A bar chart listing the top 5 countries by proxy count.

## Technical Implementation

*   **Data Source**: Fetches `metadata.json` and `summary.json` from the `output/` directory.
*   **Rendering**: Vanilla JavaScript with direct DOM manipulation for speed.
*   **Performance**: The 3D globe is lazy-loaded or paused when not in the viewport to save GPU cycles on mobile devices.
