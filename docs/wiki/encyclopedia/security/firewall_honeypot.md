# Firewalls & Honeypots

## The Great Firewall (GFW) — China
The world's most sophisticated censorship system. Techniques include:
*   **DNS Poisoning:** Returning fake IP addresses for blocked domains (e.g., `google.com` resolves to `127.0.0.1` or a random IP). ConfigStream counters this with DNS-Safe (IP-only) and DNS-Hardened (DoH/DoT) output profiles.
*   **IP Blocking:** Blacklisting specific IP addresses or entire IP ranges (ASN-level). The GFW maintains dynamic blocklists updated in real-time.
*   **SNI Blocking:** Inspecting the TLS `Server Name Indication` field to block specific sites even on shared IPs. This is why ESNI/ECH and TLS fragmentation matter.
*   **Active Probing:** The firewall acts like a "hacker." When it sees suspicious traffic (e.g., a Shadowsocks-like entropy pattern), it records the destination IP:port. Minutes later, automated probers connect to that endpoint mimicking a client. If the server responds like a proxy, the IP is blacklisted. This is why Reality and Trojan are valuable — probers see a legitimate website, not a proxy.
*   **TCP RST Injection:** Sending forged TCP Reset packets to both client and server to kill connections to blocked destinations.
*   **Throttling:** Rather than outright blocking, the GFW sometimes throttles VPN-like traffic to make it unusable (adding seconds of latency). This affects WireGuard/WARP during heavy censorship periods.

## Iran's Censorship System
Iran uses a different but equally aggressive approach:
*   **Protocol Whitelisting:** During internet shutdowns, only specific protocols (HTTP, DNS) are allowed. All UDP traffic except DNS is blocked. This makes Hysteria2/TUIC/WARP unusable during shutdowns.
*   **SNI Blocking:** Extensive domain-based blocking via SNI inspection. Thousands of domains are blocked including social media, news, and VPN providers.
*   **IP Blocking:** Known VPN provider IP ranges are blocked. DigitalOcean, Hetzner, and other popular hosting providers are frequently targeted.
*   **DPI (Deep Packet Inspection):** Iran deploys DPI hardware from Chinese vendors. It can detect Shadowsocks, OpenVPN, and WireGuard by their handshake patterns.
*   **Bandwidth Throttling:** During political events, international bandwidth is severely throttled (sometimes to 128 Kbps), making all but the lightest proxy protocols unusable.
*   **Domestic Bypass:** Local Iranian services (banks, government sites, `.ir` domains) are not filtered. ConfigStream's routing rules send domestic traffic direct.

## Russia's Censorship System (TSPU)
Russia uses TSPU (Technical Means of Countering Threats) boxes installed at ISPs:
*   **DPI-Based Blocking:** TSPU inspects traffic in real-time and can block VPN protocols including OpenVPN, WireGuard, and some Shadowsocks implementations.
*   **Protocol Detection:** Russian DPI is known to detect and throttle VPN traffic based on statistical analysis of packet sizes and timing.
*   **Selective Blocking:** Unlike China's comprehensive approach, Russia blocks specific services (Telegram, certain VPNs) while leaving most internet accessible. This makes proxy cascading through a local Russian server often viable.

## Honeypots
A honeypot is a trap set to detect, deflect, or counteract attempts at unauthorized use of information systems.
*   **Proxy Honeypots:** Malicious actors (or intelligence agencies) set up free, open proxies. When you connect, they log your traffic, IP, and destination. They may also inject malware or redirect to phishing pages.
*   **Signs of a Honeypot:**
    *   Open proxy on suspicious ports (22, 23, 25, 445).
    *   Always "up" but extremely slow or returns garbled data.
    *   Accepts all protocols but passes no real traffic.
    *   Located in a country with no logical reason to host free proxies.
    *   IP has bad reputation on VirusTotal or appears on FireHol blocklists.
*   **Detection in ConfigStream:**
    *   VirusTotal API checks for IP reputation.
    *   FireHol Level 1 blocklist integration.
    *   Heuristic analysis: proxies that "succeed" the handshake but fail to pass real traffic are flagged.
    *   Port filtering: suspicious ports are deprioritized.
    *   Source reputation: trusted sources (verified GitHub repos) weighted higher than anonymous Pastebins.

## How ConfigStream Defends

### Protocol Selection
1.  **Reality/VLESS:** Looks like normal HTTPS browsing. Active probers see a legitimate website.
2.  **Trojan:** Wrong password → serves a real website. Indistinguishable from HTTPS.
3.  **Worker Masquerading:** Root URL serves a legitimate website (kernel.org). Proxy tunnel hidden behind a secret path.

### Network Resilience
4.  **Clean IP Chaining:** Hides the true destination behind a Cloudflare IP (shielding).
5.  **Multi-Strategy Auto-Chain:** Tries 6 different strategies to find a working path — not just WARP.
6.  **Intranet Relay Discovery:** Finds LAN hosts with less-filtered access to use as stepping stones.
7.  **Circuit Breakers:** If a server fails repeatedly, stop trying it to avoid triggering censor attention.

### Data Safety
8.  **Blocklists:** FireHol Level 1 and custom blocklists filter known malicious IPs.
9.  **VirusTotal Scanning:** Optional IP reputation checking.
10. **Log Sanitization:** All logs are sanitized to remove tokens, passwords, and UUIDs — even if the pipeline is compromised, user credentials are not exposed.
11. **Anomaly Detection:** Source quality tracking flags sources that suddenly produce suspicious proxies.
