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
*   **Buckets**: <500ms, 500-1000ms, 1000-2000ms, >2000ms.
*   **Insight**: Demonstrates the quality of the "Refining" process. A left-skewed graph (towards lower latency) indicates a high-quality batch.

#### 4. Top ISPs (Internet Service Providers)
*   **Type**: Horizontal Bar Chart.
*   **Data**: Top 10 ASNs (Autonomous Systems) hosting the proxies.
*   **Insight**: Reveals infrastructure trends (e.g., "Are most proxies on DigitalOcean or Cloudflare?").

### Historical Trends (Future Roadmap)
*   We plan to add a time-series graph showing the total proxy count over the last 30 days to visualize network stability and growth.

## Technical Implementation

*   **Data Source**: `metadata.json` (specifically the `stats` and `latency_distribution` fields).
*   **Responsiveness**: Charts automatically resize for mobile/desktop screens.
*   **Interaction**: Tooltips provide exact counts and percentages on hover.
