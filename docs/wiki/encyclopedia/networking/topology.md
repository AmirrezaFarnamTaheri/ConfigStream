# Network Topology & Routing

This document explains how the internet is structured, why some proxies are fast and others slow, and how ConfigStream builds multi-hop chains to navigate around censorship.

> **Analogy**: The internet is not a cloud — it's a highway system. ISPs are the highway operators. ASNs are the cities connected by highways. Peering is a direct road between two cities. Transit is paying a trucking company to carry your cargo through multiple cities. ConfigStream's job is to find the fastest, least-policed route from your city to your destination.

---

## ASN (Autonomous System Number)

The Internet is a network of networks. Each major network (ISP, university, hosting provider) is an **Autonomous System (AS)** identified by a unique number (ASN).

*   **Role**: When you connect to a proxy, you aren't just connecting to an IP — you're connecting to an ASN. The ASN determines the network's reputation, peering quality, and censorship risk.
*   **Blocking**: Censors often block entire ASNs rather than individual IPs. Iran blocks DigitalOcean (AS14061), Hetzner (AS24940), and Vultr (AS20473) ranges. This is cheaper than blocking individual IPs.
*   **ConfigStream Strategy**: The [Source Quality Tracker](../../project/04-engineering.md) analyzes ASN diversity. If 100 working proxies all come from the same ASN, and that ASN gets throttled, the user loses everything. We aim for a mix across multiple providers and countries.
*   **Lookup**: Check an IP's ASN at [bgp.tools](https://bgp.tools/) or using `whois`.

> **Example**: A source provides 50 proxies, all on Hetzner (AS24940). Iran blocks Hetzner. All 50 proxies are dead for Iranian users. A diverse source with 10 proxies across 8 ASNs loses only 1-2 when a single ASN is blocked.

---

## Network Topology

This refers to the map of how data flows through the internet.

*   **Peering**: Direct connections between ISPs. Peering is free and fast. If your ISP peers directly with the proxy's hosting provider, latency is low.
    > **Example**: An Iranian user on MCI (AS197207) connecting to a proxy on Cloudflare (AS13335) gets ~30ms latency because MCI peers directly with Cloudflare at the Tehran IXP. The same user connecting to a proxy on a small German VPS provider gets ~200ms because traffic must transit through 5+ intermediate networks.
*   **Transit**: Paying an upstream provider (like Level3 or Cogent) to carry traffic. Transit adds hops and cost.
*   **IXP (Internet Exchange Point)**: A physical location where ISPs connect to exchange traffic. Major IXPs include DE-CIX (Frankfurt), AMS-IX (Amsterdam), and LINX (London). Proxies hosted near an IXP often have better connectivity.
*   **Optimized Routing**: A proxy might be fast not because the server is powerful, but because it has a better "route" (topology path) to the user's ISP (e.g., CN2 GIA for China, NTT for Japan).

> **Why this matters for ConfigStream**: The [Pareto Sort algorithm](../../project/04-engineering.md) ranks proxies by latency, failure rate, and stability. A proxy with great peering to your ISP will naturally rank higher — even if the server itself is modest hardware.

---

## Chaining (Proxy Chaining)

Routing traffic through multiple proxies in sequence.

```
Client → Proxy A (relay) → Proxy B (exit) → Target
```

**Three reasons to chain**:
1.  **Anonymity**: Proxy B knows the target but not the client. Proxy A knows the client but not the target. Neither has the full picture.
2.  **Unblocking (Washing/Shielding)**: If the user cannot reach Proxy B directly (blocked IP), they use Proxy A (clean IP) to reach it. See [WARP & Clean IPs](warp.md).
3.  **Jurisdiction Diversity**: Each hop can be in a different legal jurisdiction, making surveillance harder. A 3-hop chain across Singapore → Germany → USA crosses three legal systems.

**Latency cost**: Each hop adds 50-200ms. A 2-hop chain typically adds 100-300ms total. For browsing this is acceptable; for gaming or VoIP, use [Low Latency chains](../../project/04-engineering.md) which minimize hop distance.

> **Analogy**: Chaining is like sending a letter through multiple post offices. Each office only knows where the letter came from and where it's going next — not the original sender or final destination. The trade-off is delivery time.

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
*   **Discovery:** Run `python tools/lab-scanner.py --scan-relays` to probe LAN subnets and user-supplied hosts for reachable SOCKS/HTTP services with internet access.
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

---

## Intranet vs. Internet

*   **Intranet**: The local network (LAN) within an organization — typically `192.168.x.x`, `10.x.x.x`, or `172.16-31.x.x` ranges. Machines on the intranet may have different levels of internet access.
*   **Internet**: The global public network. Censorship operates at the boundary between intranet and internet (the ISP/gateway).
*   **Key Insight**: Not all machines on your LAN are equally censored. A server room machine, a VPN gateway, or a privileged workstation may have unrestricted access.

> **Example**: In a university network, student WiFi is heavily filtered (no Telegram, no YouTube). But the research lab's server at `10.0.5.20` has unrestricted access for downloading datasets. If that server runs an HTTP proxy on port 3128, you can chain through it: `Your laptop → 10.0.5.20:3128 → VLESS server → Internet`. ConfigStream's `--scan-relays` discovers these "stepping stones" automatically by probing LAN subnets for reachable SOCKS/HTTP services.

## Related Documentation

*   **[WARP & Clean IPs](warp.md)** — How Cloudflare WARP integrates into multi-hop chains and shielding topology.
*   **[Engineering Internals — Smart Chains](../../project/04-engineering.md)** — 95-country geographic database, scoring algorithm, 9 chain types, censorship levels.
*   **[Architecture Deep Dive](../../project/02-architecture.md)** — Pipeline sharding, intelligence synchronization across VMs.
*   **[Firewalls & Honeypots](../security/firewall_honeypot.md)** — How ASN-level blocking and IP blocking work in practice.
*   **[Networking Terms](../glossary/networking_terms.md)** — ISP, CDN, route, QUIC — the building blocks of network topology.
