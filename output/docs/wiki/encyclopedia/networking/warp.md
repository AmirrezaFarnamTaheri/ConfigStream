# Cloudflare WARP

## Overview
Cloudflare WARP is a free VPN service built on top of the **WireGuard** protocol. It routes traffic through Cloudflare's massive global network, providing privacy and performance improvements.

## Relevance to Censorship Circumvention
WARP is unique because:
1.  **Global Anycast:** It uses the same IP addresses (e.g., `162.159.192.1`) worldwide.
2.  **UDP Transport:** It uses standard WireGuard UDP packets.
3.  **Resilience:** Because Cloudflare powers a huge portion of the internet, completely blocking their IP ranges causes massive collateral damage.

## The "Dirty IP" Problem
In some restrictive regions (Iran, Russia, China), the default endpoint IPs for WARP are blocked or throttled. However, because Cloudflare's network is **Anycast**, *thousands* of other IPs can accept WARP traffic.

## Clean IP Scanning
ConfigStream exploits the Anycast nature of WARP. We scan for "Clean IPs"—Cloudflare edge IPs that:
1.  Are reachable from the user's location (low latency).
2.  Accept WireGuard handshakes on the correct port (usually 2408 or random).
3.  Are not currently in the censor's blacklist.

By modifying the `endpoint` field in a WireGuard config to point to a Clean IP, we can "wash" the connection and restore access.
