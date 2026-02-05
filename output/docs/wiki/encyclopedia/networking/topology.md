# Network Topology & Routing

## ASN (Autonomous System Number)
The Internet is not a single cloud; it's a network of networks. Each major network (like an ISP, a University, or a Hosting Provider) is an **Autonomous System (AS)** identified by a unique number (ASN).
*   **Role:** When you connect to a proxy, you aren't just connecting to an IP; you are connecting to an ASN.
*   **Blocking:** Censors often block entire ASNs (e.g., blocking all of DigitalOcean or Hetzner) rather than individual IPs.
*   **ConfigStream Strategy:** We analyze ASNs to ensure diversity. If 100 working proxies all come from the same ASN (e.g., Cloudflare), and that ASN gets throttled, the user loses everything. We aim for a mix.

## Network Topology
This refers to the map of how data flows through the internet.
*   **Peering:** Direct connections between ISPs.
*   **Transit:** Paying an upstream provider (like Level3 or Cogent) to carry traffic.
*   **Optimized Routing:** A proxy might be fast not because the server is powerful, but because it has a better "route" (topology path) to the user's ISP (e.g., CN2 GIA for China).

## Chaining (Proxy Chaining)
Routing traffic through multiple proxies in sequence.
*   **Structure:** `Client -> Proxy A -> Proxy B -> Target`
*   **Purpose:**
    1.  **Anonymity:** Proxy B knows the target but not the client. Proxy A knows the client but not the target.
    2.  **Unblocking (Washing):** If the user cannot reach Proxy B directly (blocked IP), they use Proxy A (Clean IP) to reach it.
*   **Latency:** Adds latency because data must hop twice.
