# Security & Intelligence

## Zero Abuse Policy
ConfigStream strictly adheres to a "No Active Abuse" policy to maintain its free infrastructure.
*   **No Port Scanning:** We do not connect to ports 22 (SSH), 23 (Telnet), or 3389 (RDP) to verify servers. This is flagged as malicious by cloud providers (Azure/GitHub Actions).
*   **Passive Only:** We rely on passive signals like VirusTotal API and ASN reputation to identify bad actors.

## Honeypot Detection (Passive Mode)
Surveillance nodes often pose as open proxies.
1.  **VirusTotal API:** Check if the IP is flagged as a scanner/botnet.
2.  **ASN Reputation:** Block known "Bulletproof Hosting" or "Research Scanner" ASNs.
3.  **Behavioral Analysis:** If a source provides 10,000 proxies and 99% fail, the entire batch is flagged as "Poisoned".

## Proxy Washing
Many free proxies work but are blocked by Google/Cloudflare (403 Forbidden).
**The Solution:** We use them as a transport layer for a clean WireGuard tunnel.

1.  **The Dirty Proxy:** A VLESS node in Iran (blocked by Google).
2.  **The Cleaner:** Cloudflare WARP (free WireGuard).
3.  **The Chain:** `Client -> VLESS (Iran) -> WARP -> Google`.

This allows us to recycle "useless" proxies into high-quality VPN connections.

## Smart Chains
### Intranet Bridges
We automatically detect proxies that are on the same domestic intranet (e.g., China Mobile to China Mobile) and chain them to an exit node to bypass throttling.

### IPv6 Portals
If a proxy supports IPv6 but the client doesn't, we chain it:
`Client (IPv4) -> Relay (Dual Stack) -> Target (IPv6)`
