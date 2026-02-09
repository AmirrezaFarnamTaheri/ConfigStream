# Network Topology & Routing

## ASN (Autonomous System Number)
The Internet is not a single cloud; it's a network of networks. Each major network (like an ISP, a University, or a Hosting Provider) is an **Autonomous System (AS)** identified by a unique number (ASN).
*   **Role:** When you connect to a proxy, you aren't just connecting to an IP; you are connecting to an ASN.
*   **Blocking:** Censors often block entire ASNs (e.g., blocking all of DigitalOcean or Hetzner) rather than individual IPs. This is called **ASN-level blocking**.
*   **ConfigStream Strategy:** We analyze ASNs to ensure diversity. If 100 working proxies all come from the same ASN (e.g., Cloudflare), and that ASN gets throttled, the user loses everything. We aim for a mix across multiple providers and countries.
*   **Lookup:** You can check an IP's ASN at [bgp.tools](https://bgp.tools/) or using `whois`.

## Network Topology
This refers to the map of how data flows through the internet.
*   **Peering:** Direct connections between ISPs. Peering is free and fast. If your ISP peers directly with the proxy's hosting provider, latency is low.
*   **Transit:** Paying an upstream provider (like Level3 or Cogent) to carry traffic. Transit adds hops and cost.
*   **IXP (Internet Exchange Point):** A physical location where ISPs connect to exchange traffic. Major IXPs include DE-CIX (Frankfurt), AMS-IX (Amsterdam), and LINX (London). Proxies hosted near an IXP often have better connectivity.
*   **Optimized Routing:** A proxy might be fast not because the server is powerful, but because it has a better "route" (topology path) to the user's ISP (e.g., CN2 GIA for China, NTT for Japan).

## Chaining (Proxy Chaining)
Routing traffic through multiple proxies in sequence.
*   **Structure:** `Client -> Proxy A -> Proxy B -> Target`
*   **Purpose:**
    1.  **Anonymity:** Proxy B knows the target but not the client. Proxy A knows the client but not the target.
    2.  **Unblocking (Washing):** If the user cannot reach Proxy B directly (blocked IP), they use Proxy A (Clean IP) to reach it.
    3.  **Jurisdiction Diversity:** Each hop can be in a different legal jurisdiction, making surveillance harder.
*   **Latency:** Adds latency because data must hop twice. Typical overhead: 50-200ms per hop.

### Chaining Strategies in ConfigStream

ConfigStream and the Lab Scanner support multiple chaining strategies beyond just WARP:

#### 1. Direct Proxy (No Chain)
```
[You] → [Proxy] → [Internet]
```
*   **When:** The proxy is directly reachable from your network. No tunnel needed.
*   **Advantage:** Lowest latency, simplest setup.

#### 2. Proxy Cascade
```
[You] → [Local Proxy A] → [Proxy B] → [Internet]
```
*   **When:** You have a local circumvention tool (Psiphon, Lantern, Tor, V2Ray) that provides internet access, and you want to chain a destination proxy on top.
*   **Example:** Psiphon (SOCKS5 at `127.0.0.1:1080`) → VLESS server in Germany.
*   **Advantage:** No Cloudflare/WARP needed. Works even when WARP is blocked.
*   **Lab Scanner:** `--auto-chain` Strategy 2 automatically discovers and chains local proxies.

#### 3. Relay Hop
```
[You] → [LAN Relay] → [Proxy] → [Internet]
```
*   **When:** A machine on your local network (corporate proxy, university gateway, colleague's computer) has less-filtered internet access.
*   **Example:** Corporate HTTP proxy at `10.0.0.50:3128` → VLESS server.
*   **Discovery:** Run `python lab-scanner.py --scan-relays` to probe LAN subnets and user-supplied hosts for reachable SOCKS/HTTP services with internet access.
*   **Advantage:** Uses infrastructure already present on your network. Zero external dependencies.

#### 4. WARP Tunnel
```
[You] → [WARP (Clean IP)] → [Proxy] → [Internet]
```
*   **When:** Direct proxy access is blocked but Cloudflare IPs are reachable.
*   **See:** [WARP documentation](warp.md) for details on clean IP scanning and shielding.

#### 5. Local Proxy + WARP
```
[You] → [Local Proxy] → [WARP] → [Proxy] → [Internet]
```
*   **When:** Both direct proxy and direct WARP access are blocked, but a local proxy can reach WARP.
*   **3-hop chain:** Higher latency but works in extremely restrictive environments.

#### 6. LAN Relay + WARP
```
[You] → [LAN Relay] → [WARP] → [Proxy] → [Internet]
```
*   **When:** You cannot reach WARP directly, but a LAN machine can.
*   **Most resilient:** Combines intranet access with WARP tunneling.

### ConfigStream Smart Chains (Pipeline Output)
The pipeline generates 9 types of smart chains automatically:
1.  **Intranet** — Standard 2-hop through regional relay.
2.  **Intranet Washed** — 3-hop with WARP tunnel.
3.  **IPv6 Portal** — Dual-stack relay to IPv6-only exit.
4.  **Streaming Accelerator** — Fast UDP protocol (Hysteria2/TUIC) for low-latency streaming.
5.  **Censorship Resistant** — Stealth protocol (VLESS/Trojan) through jurisdiction transition.
6.  **Low Latency** — Speed-optimized relay selection for gaming/VoIP.
7.  **High Anonymity** — 3-hop cross-continental for maximum privacy.
8.  **Load Balanced** — Multiple paths to same destination for failover.
9.  **Experimental** — Protocol wrapping experiments.

## Intranet vs. Internet
*   **Intranet:** The local network (LAN) within an organization — typically `192.168.x.x`, `10.x.x.x`, or `172.16-31.x.x` ranges. Machines on the intranet may have different levels of internet access.
*   **Internet:** The global public network. Censorship operates at the boundary between intranet and internet (the ISP/gateway).
*   **Key Insight:** Not all machines on your LAN are equally censored. A server room machine, a VPN gateway, or a privileged workstation may have unrestricted access. ConfigStream's `--scan-relays` discovers these "stepping stones."
