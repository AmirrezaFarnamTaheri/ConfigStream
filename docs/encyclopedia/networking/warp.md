# Cloudflare WARP & Clean IPs

**WARP** is Cloudflare's VPN service based on WireGuard. ConfigStream uses WARP for "Washing" (reviving dead proxies) and "Shielding" (protecting proxy IPs).

## Concepts

### Washing (Revival)
When a proxy is blocked or marked as "dirty" (e.g. Google Captcha), we wrap it in a WARP tunnel.
**Topology**: `Client -> Proxy -> WARP -> Internet`
This hides the proxy's IP from the destination (Netflix, Google).

### Shielding (Gold)
When a proxy is blocked by the ISP (Firewall), we wrap the connection to the proxy in a WARP tunnel.
**Topology**: `Client -> WARP -> Proxy -> Internet`
This hides the proxy's IP from the ISP. Requires a "Clean IP" for the WARP endpoint.

### Clean IPs
A "Clean IP" is a Cloudflare endpoint IP (usually `162.159.x.x`) that is reachable from the user's network. ConfigStream actively scans for these IPs to ensure connectivity.

## Vwarp
**Vwarp** is a specialized tool used by ConfigStream to manage WARP keys, generate configs, and perform advanced obfuscation (Masque/Quic) to bypass WARP blocks.
