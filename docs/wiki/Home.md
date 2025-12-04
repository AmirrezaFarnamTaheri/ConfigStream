# ConfigStream Wiki

Welcome to the **ConfigStream** documentation. ConfigStream is an automated, high-performance VPN configuration aggregator designed to provide reliable, free access to the open internet.

## Core Concepts

*   **Zero Budget Architecture:** The system runs entirely on free, resilient cloud infrastructure (GitHub Actions, Pages, Cloudflare), ensuring long-term sustainability and censorship resistance.
*   **Hybrid Engine:** We combine the flexibility of **Python** for data processing and intelligence with the raw performance of **Go** for massive-scale network testing.
*   **Smart Routing ("The Sniper"):** Our configurations are optimized to route traffic intelligently, bypassing restrictions while maintaining speed.
*   **Proxy Washing:** blocked IPs are automatically "washed" through Cloudflare WARP to restore connectivity.

## Getting Started

1.  **Download:** Visit the [Home Page](../index.html) to get the latest subscription links.
2.  **Import:** Use a compatible client like **V2RayNG**, **Shadowrocket**, **Streisand**, or **Hiddify**.
3.  **Connect:** Select a proxy and connect.

## Documentation Index

*   **[Architecture](Architecture_v2.md):** A deep dive into how ConfigStream works under the hood.
*   **[Troubleshooting](Troubleshooting.md):** Solutions for common connection issues.
*   **[Contributing](09-contributing.md):** How developers can help improve the project.
*   **[API Reference](08-api-reference.md):** Details on the data structures and endpoints.

## Legal & Security

These configurations are aggregated from public sources. While we perform rigorous automated security checks (filtering malware, honeypots, and invalid certs), usage is at your own risk. We recommend avoiding sensitive transactions (banking) over public proxies.
