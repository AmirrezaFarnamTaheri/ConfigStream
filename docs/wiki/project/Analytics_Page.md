# Analytics Page Documentation

The **Analytics** page is the transparency engine of ConfigStream. It transforms raw data into actionable insights, allowing users and developers to understand the dynamics of the proxy ecosystem.

## Design Philosophy: "Trust Through Data"

We believe that open-source tools must be transparent. By exposing the internal metrics of our pipeline—success rates, latency distributions, and source reliability—we prove the system's efficacy.

### Key Visualizations

#### 1. Latency Heatmap (The World Map)
*   **Library**: `Chart.js` (Choropleth extension) or Custom SVG Map.
*   **Data**: Average latency per country code (ISO 3166-1 alpha-2).
*   **Insight**: Users can instantly see which regions offer the fastest connection speeds.
*   **Color Scale**: Green (Low Latency) -> Red (High Latency) -> Grey (No Data).

#### 2. Protocol Breakdown
*   **Type**: Doughnut / Pie Chart.
*   **Data**: Count of unique proxies per protocol (VLESS, VMess, Trojan, Shadowsocks, etc.).
*   **Insight**: Shows the diversity of the network. A healthy network has a balanced mix, preventing total blockage if one protocol is targeted by censors.

#### 3. Latency Distribution (The Bell Curve)
*   **Type**: Histogram.
*   **Buckets**: <200ms, 200-800ms, 800-2000ms, >2000ms.
*   **Insight**: Demonstrates the quality of the "Refining" process. A left-skewed graph (towards lower latency) indicates a high-quality batch.

#### 4. Top ISPs (Internet Service Providers)
*   **Type**: Horizontal Bar Chart.
*   **Data**: Top 10 ASNs (Autonomous Systems) hosting the proxies.
*   **Insight**: Reveals infrastructure trends (e.g., "Are most proxies on DigitalOcean or Cloudflare?").

#### 5. Evasion Trend (Time-Series) 
*   **Type**: Multi-line chart with fill.
*   **Data**: `data/evasion_trend.json` — rolling 7-day window of evasion metrics.
*   **Datasets**:
    *   Shielded (Gold) proxy count
    *   Revived (WARP) proxy count
    *   Revived (VWARP) proxy count
    *   uTLS-enabled proxy count
    *   DNS-Hardened proxy count
*   **Insight**: Tracks the effectiveness of evasion features over time. Increasing trends indicate successful censorship resistance; decreasing trends may signal censor adaptation.

#### 6. Active Proxy Trend Dataset
*   **Data**: `data/active_proxy_trend.json` — hourly buckets over 7 days.
*   **Current consumer**: Published as a stable static artifact for API and downstream use; the first-party analytics page does not currently render it.
*   **Insight**: Supports external analysis of network stability and growth without overstating a browser visualization that is not implemented.

#### 7. Rejection Reasons
*   **Type**: Pie chart.
*   **Data**: `metadata.json` → `rejection_reasons`.
*   **Insight**: Shows why proxies were dropped (dirty IP, timeout, handshake fail, parse error).

#### 8. Latency by Protocol
*   **Type**: Bar chart.
*   **Data**: `metadata.json` → `latency_by_protocol`.
*   **Insight**: Compares average latency across protocols (VLESS vs Trojan vs Hysteria2 etc).

### 3D Globe Visualization
*   **Library**: `globe.gl` (WebGL / Three.js).
*   **Data**: Country-level proxy counts from `metadata.json` → `country_stats`, with centroid lookup.
*   **Fallback**: If `proxy_locations` array is present, uses per-proxy lat/lng with latency-based coloring.
*   **Interaction**: Auto-rotates, pauses on user interaction, resumes after 2s idle.

## Technical Implementation

*   **Data Sources**:
    *   `metadata.json` — `latency_distribution`, `latency_by_country`, `latency_by_protocol`, `protocols`, `country_stats`, `asns`, `rejection_reasons`
    *   `data/evasion_trend.json` — evasion metrics time-series
    *   `data/active_proxy_trend.json` — active proxy count time-series
*   **Responsiveness**: Charts automatically resize for mobile/desktop screens.
*   **Interaction**: Tooltips provide exact counts and percentages on hover.
*   **Color Logic**: Centralized `generateColor()` function using consistent label hashing for deterministic colors across charts.
