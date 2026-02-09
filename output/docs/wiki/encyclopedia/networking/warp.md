# Cloudflare WARP

## Overview
Cloudflare WARP is a free VPN service built on top of the **WireGuard** protocol. It routes traffic through Cloudflare's massive global network, providing privacy and performance improvements. WARP is one of ConfigStream's most powerful tools — but it is **not the only strategy**. See the section on alternatives below.

## How WARP Works
1.  **WireGuard Tunnel:** WARP creates an encrypted WireGuard tunnel between your device and a Cloudflare edge server.
2.  **Anycast Routing:** Traffic enters Cloudflare's network at the nearest edge server and is routed internally. This means the same IP addresses (e.g., `162.159.192.1`) work from anywhere in the world.
3.  **Key Pair:** Each WARP client has a private key and Cloudflare has a public key (`bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=`). The handshake proves identity without revealing traffic content.
4.  **Free Tier:** WARP is free and does not require registration. WARP+ (paid) routes through optimized paths but is not needed for basic censorship circumvention.

## Relevance to Censorship Circumvention
WARP is unique because:
1.  **Global Anycast:** It uses the same IP addresses worldwide. There is no single "WARP server" to block.
2.  **UDP Transport:** It uses standard WireGuard UDP packets on various ports (500, 854, 859, 864, 878, 880, 890, 891, 894, 903, 908, 928, 934, 939, 942, 943, 945, 946, 955, 968, 987, 988, 1002, 1010, 1014, 1018, 1070, 1074, 1180, 1387, 1843, 2371, 2408, 2506, 3138, 3476, 3581, 3854, 4177, 4198, 4233, 5765, 5956, 7103, 7152, 7156, 7281, 7559, 8319, 8742, 8854, 8886).
3.  **Collateral Damage:** Because Cloudflare powers ~20% of the internet, completely blocking their IP ranges breaks thousands of legitimate websites (banks, news, e-commerce). Censors typically throttle rather than fully block.

## The "Dirty IP" Problem
In some restrictive regions (Iran, Russia, China), the default endpoint IPs for WARP are blocked or throttled. However, because Cloudflare's network is **Anycast**, *thousands* of other IPs can accept WARP traffic. The censor blocks specific IPs, but there are always more.

## Clean IP Scanning
ConfigStream exploits the Anycast nature of WARP. We scan for "Clean IPs" — Cloudflare edge IPs that:
1.  **Are reachable** from the user's location (low latency, not blocked).
2.  **Accept WireGuard handshakes** on one of the many supported ports.
3.  **Are not currently blacklisted** by the censor.

### How the Scanner Works (`lab-scanner.py`)
1.  **IP Pool:** Tests 34+ Cloudflare IPs across 34+ ports (1,156+ combinations).
2.  **Dual Probe:** Sends both UDP probes (WireGuard handshake initiation) and TCP connect tests.
3.  **Latency Ranking:** Sorts results by response time — lower latency means better peering with your ISP.
4.  **Alt CDN IPs:** Also tests non-Cloudflare IPs (Fastly, Google, Meta, Microsoft, Telegram, GitHub) to find alternative paths.
5.  **User IPs:** Accepts user-supplied IPs (`--custom-ips`) merged into the scan.

### Port Diversity
Censors often block specific ports. WARP supports **50+ ports** across multiple ranges. The scanner tests all of them to find which ports are open on your network. Common successful ports include 854, 890, 2408, 500, and 943.

## WARP Chain Topologies

### Standard Washing
```
[You] → [Proxy] → [WARP] → [Internet]
```
*   **Purpose:** Hides the proxy's exit IP from the destination. Useful for unblocking geo-restricted services (Netflix, Google).
*   **Limitation:** If the proxy IP is blocked by your ISP, you cannot connect in the first place.

### Shielding (Topology Inversion)
```
[You] → [WARP (Clean IP)] → [Proxy] → [Internet]
```
*   **Purpose:** Hides the proxy IP from your ISP. Your ISP only sees a connection to a Cloudflare IP (which they cannot block without breaking the internet).
*   **Tag:** Proxies using this topology are tagged `GOLD-` in ConfigStream output.
*   **Implementation:** `ProxyWasher.shield_batch()` automatically creates shielded configs for failed proxies.

### Double WARP (WARP-in-WARP)
```
[You] → [Outer WARP] → [Inner WARP] → [Proxy] → [Internet]
```
*   **Purpose:** Maximum obfuscation. Two layers of WireGuard encryption. Even if someone compromises one WARP node, they cannot see your traffic.
*   **Use Case:** High-threat environments where traffic correlation attacks are a concern.

## Alternatives to WARP

WARP is powerful but not the only strategy. When WARP is blocked or unavailable:

1.  **Proxy Cascade:** Chain local proxies together (e.g., Psiphon → V2Ray → Internet). No Cloudflare needed.
2.  **Intranet Relay:** Find a machine on your LAN with less-filtered internet access and route through it. Run `python lab-scanner.py --scan-lan` to discover relays.
3.  **TLS Fragment:** Split the TLS handshake into fragments to evade DPI. Works without any tunnel.
4.  **CDN Worker:** Route through your own Cloudflare Worker. The Worker URL is unique to you and very hard to block.
5.  **Direct Proxy:** If your proxy is directly reachable (not blocked), no tunnel is needed at all.

ConfigStream's `--auto-chain` tries all 6 strategies automatically and picks the best working path.

## WARP Key Management
*   **Free Tier:** Works without a key. Traffic is encrypted but routed through standard paths.
*   **WARP+ Key:** Format `xxxxxxxx-xxxxxxxx-xxxxxxxx`. Provides optimized routing (Argo Smart Routing). Optional — free tier is sufficient for circumvention.
*   **Key Source:** Users can obtain WARP+ keys from various Telegram bots and communities. ConfigStream does not generate or distribute keys.

## Technical Details

### WireGuard Configuration Fields
```json
{
  "type": "wireguard",
  "server": "162.159.192.1",
  "server_port": 2408,
  "local_address": ["172.16.0.2/32", "fd01:db8:85a3::2/128"],
  "private_key": "...",
  "peer_public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
  "mtu": 1280
}
```

### Reserved Field
The `reserved` field (`[0, 0, 0]` by default) is a 3-byte client identifier used by Cloudflare for WARP+ routing. For free-tier usage, it can be left as zeros.
