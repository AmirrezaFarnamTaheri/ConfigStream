# Firewalls & Honeypots

This document describes the major censorship systems ConfigStream is designed to defeat, how proxy honeypots work, and which protocols survive in each environment.

> **Analogy**: Censorship systems are like border checkpoints with different levels of sophistication. Some just check your passport (IP blocking). Some X-ray your luggage (DPI). Some send undercover agents to test if you're smuggling (active probing). ConfigStream gives you a different disguise for each checkpoint.

---

## The Great Firewall (GFW) — China

The world's most sophisticated censorship system, operated by the Cyberspace Administration of China. It combines multiple techniques simultaneously:

### DNS Poisoning
Returning fake IP addresses for blocked domains. When you query `google.com`, the GFW intercepts the DNS response and replaces it with `127.0.0.1` or a random IP — before the real answer arrives.

> **Example**: `dig google.com` from inside China returns `203.98.7.65` (a fake IP). From outside China, it returns `142.250.80.46` (the real IP). ConfigStream counters this with [DNS-Safe](../../../CENSORSHIP_EVASION.md) (pre-resolved IPs) and DNS-Hardened ([DoH/DoT/DoQ](../glossary/networking_terms.md)) output profiles.

### IP Blocking
Blacklisting specific IP addresses or entire IP ranges (ASN-level). The GFW maintains dynamic blocklists updated in real-time. When a proxy server is discovered, its IP is blocked within minutes.

### [SNI](../glossary/networking_terms.md) Blocking
Inspecting the TLS Server Name Indication field to block specific sites even on shared IPs. The SNI is sent in cleartext during the TLS handshake, so the GFW can read it without decrypting anything.

### [Active Probing](../glossary/security_concepts.md)
The GFW's most dangerous technique. When it sees suspicious traffic (e.g., a [Shadowsocks](../protocols/shadowsocks.md)-like [entropy](../glossary/security_concepts.md) pattern), it records the destination IP:port. Minutes later, automated probers connect to that endpoint mimicking a client. If the server responds like a proxy, the IP is blacklisted.

> **Real-world timeline**: User connects to SS server at 14:00. GFW flags the traffic at 14:01. Prober connects to the same IP:port at 14:03. Server responds to the probe. IP is blocked by 14:05. Total time from first connection to block: **5 minutes**.

This is why [Reality](../protocols/vless.md) and [Trojan](../protocols/trojan.md) are valuable — probers see a legitimate website, not a proxy.

### TCP RST Injection
Sending forged TCP Reset packets to both client and server to kill connections to blocked destinations. Both sides think the other closed the connection.

### Throttling
Rather than outright blocking, the GFW sometimes throttles VPN-like traffic to make it unusable (adding seconds of latency). This affects [WireGuard](../protocols/wireguard.md)/WARP during heavy censorship periods.

---

## Iran's Censorship System

Iran uses a different but equally aggressive approach, with censorship intensity that fluctuates based on political events:

### Protocol Whitelisting (Shutdown Mode)
During internet shutdowns (protests, elections), Iran switches to a **whitelist model** — only HTTP (port 80) and DNS (port 53) are allowed. Everything else is dropped. All UDP traffic except DNS is blocked, making [Hysteria2](../protocols/hysteria2.md)/TUIC/WARP unusable.

> **When does this happen?** Major shutdowns occurred during the Mahsa Amini protests (Sep 2022), the November 2019 protests, and periodically during elections. Duration ranges from hours to weeks.

### SNI Blocking
Extensive domain-based blocking via [SNI](../glossary/networking_terms.md) inspection. Tens of thousands of domains are blocked including social media (Twitter, Facebook, YouTube, Instagram), messaging (Telegram, Signal, WhatsApp), news sites, and VPN providers.

### IP Blocking
Known VPN provider IP ranges are blocked. DigitalOcean, Hetzner, Vultr, and other popular hosting providers are frequently targeted. The blocklist is updated regularly.

### DPI (Deep Packet Inspection)
Iran deploys [DPI](../glossary/networking_terms.md) hardware (reportedly from Chinese vendors). It can detect [Shadowsocks](../protocols/shadowsocks.md), OpenVPN, and [WireGuard](../protocols/wireguard.md) by their handshake patterns. The DPI is less sophisticated than China's GFW — it doesn't do active probing — but it's effective at protocol fingerprinting.

### Bandwidth Throttling
During political events, international bandwidth is severely throttled (sometimes to 64-128 Kbps), making all but the lightest proxy protocols unusable. Domestic bandwidth remains normal.

### Domestic Bypass
Local Iranian services (banks, government sites, `.ir` domains) are not filtered. ConfigStream's [routing rules](../../../CENSORSHIP_EVASION.md) send domestic traffic direct to avoid breaking local services.

---

## Russia's Censorship System (TSPU)

Russia uses TSPU (ТСПУ — Technical Means of Countering Threats) boxes installed at ISP level:

### DPI-Based Blocking
TSPU inspects traffic in real-time and can block VPN protocols including OpenVPN, [WireGuard](../protocols/wireguard.md), and some [Shadowsocks](../protocols/shadowsocks.md) implementations.

### Protocol Detection
Russian DPI detects and throttles VPN traffic based on statistical analysis of packet sizes and timing. It's less aggressive than China's GFW but more capable than Iran's system.

### Selective Blocking
Unlike China's comprehensive approach, Russia blocks specific services (Telegram, certain VPNs, opposition media) while leaving most internet accessible. This makes proxy cascading through a local Russian server often viable — a Russian relay can reach blocked sites that a direct connection cannot.

> **Key difference from China/Iran**: Russia's censorship is more targeted. Most protocols work most of the time. The main risk is during escalation periods (war, elections) when TSPU enforcement increases.

---

## Protocol Survival Matrix

Which protocols survive in each censorship environment:

| Protocol | China (GFW) | Iran (Normal) | Iran (Shutdown) | Russia (TSPU) |
|---|---|---|---|---|
| [VLESS+Reality](../protocols/vless.md) | ✅ Best | ✅ Works | ✅ Works (TCP) | ✅ Works |
| [Trojan](../protocols/trojan.md) | ✅ Good | ✅ Works | ✅ Works (TCP) | ✅ Works |
| [VMess+WS+TLS](../protocols/vmess.md) | ✅ Good | ✅ Works | ⚠️ Slow | ✅ Works |
| [Shadowsocks](../protocols/shadowsocks.md) | ⚠️ Detectable | ✅ Works | ⚠️ Slow | ✅ Works |
| [Hysteria2](../protocols/hysteria2.md) | ⚠️ Throttled | ✅ Fast | ❌ Blocked (UDP) | ✅ Works |
| [WireGuard](../protocols/wireguard.md)/WARP | ⚠️ Throttled | ✅ Works | ❌ Blocked (UDP) | ⚠️ Detectable |
| OpenVPN | ❌ Blocked | ❌ Blocked | ❌ Blocked | ⚠️ Detectable |

**Legend**: ✅ = reliable, ⚠️ = works sometimes/degraded, ❌ = blocked

---

## Honeypots

A honeypot is a trap set to detect, deflect, or counteract attempts at unauthorized use of information systems.

> **Analogy**: A honeypot is like a fake ATM set up by police. It looks real, accepts your card, and records everything — but it's designed to catch criminals. Proxy honeypots work the same way: they accept your connection, log your traffic, and may inject malware.

### Types of Proxy Honeypots

*   **Intelligence Honeypots**: Set up by state actors to monitor dissidents. They log source IPs, destinations visited, and traffic patterns. Common in Iran and China.
*   **Criminal Honeypots**: Set up by hackers to steal credentials. They intercept unencrypted traffic (HTTP) and inject malicious JavaScript or redirect to phishing pages.
*   **Research Honeypots**: Set up by security researchers to study proxy abuse. Less dangerous but still log your traffic.

### Signs of a Honeypot

| Red Flag | Why It's Suspicious |
|---|---|
| Open proxy on port 22, 23, 25, 445 | These are SSH, Telnet, SMTP, SMB — not normal proxy ports |
| Always "up" but extremely slow | Real proxies go down; honeypots are kept alive deliberately |
| Accepts all protocols but passes no real traffic | Handshake succeeds but HTTP requests timeout |
| Located in a country with no logical reason to host free proxies | e.g., a "free proxy" in North Korea |
| IP on VirusTotal or FireHol blocklists | Known malicious infrastructure |
| Identical configs from multiple unrelated sources | Coordinated distribution of the same honeypot |

### Detection in ConfigStream

1.  **VirusTotal API**: Checks IP reputation against 70+ antivirus engines.
2.  **FireHol Level 1 Blocklist**: Curated list of known malicious IPs (botnets, spam, C2 servers).
3.  **Heuristic Analysis**: Proxies that succeed the handshake but fail to pass real traffic are flagged.
4.  **Port Filtering**: Suspicious ports are deprioritized.
5.  **Source Reputation**: Trusted sources (verified GitHub repos) weighted higher than anonymous Pastebins.
6.  **Go Sidecar Honeypot Probe**: When `strict_security` is enabled, the tester performs a UDP honeypot probe and uses a canary URL to verify the proxy actually reaches the internet.

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

## Related Documentation

*   **[Networking Terms](../glossary/networking_terms.md)** — TLS, SNI, DPI, QUIC — the technologies censors target and defenders use.
*   **[Security Concepts](../glossary/security_concepts.md)** — Active Probing, Entropy Analysis, Circuit Breaker, AEAD — the defense patterns.
*   **[VLESS Protocol](../protocols/vless.md)** — Reality defeats GFW active probing.
*   **[Trojan Protocol](../protocols/trojan.md)** — HTTPS mimicry with fallback defeats active probers.
*   **[Hysteria2 Protocol](../protocols/hysteria2.md)** — Vulnerable to Iran-style UDP blocking.
*   **[WireGuard Protocol](../protocols/wireguard.md)** — 148-byte handshake easily fingerprinted.
*   **[Censorship Evasion](../../../CENSORSHIP_EVASION.md)** — ConfigStream's eight layers of defense against these censorship systems.
*   **[Engineering Internals](../../project/04-engineering.md)** — Anomaly Detector, Source Quality Tracker, Smart Chain censorship levels.
