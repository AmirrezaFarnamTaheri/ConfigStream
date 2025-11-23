# 07. Security & Privacy

ConfigStream operates in a hostile environment. We deal with circumvention tools, which attracts attention from censors and malicious actors. Security is not an afterthought; it is the foundation.

## The Threat Model

We defend against three primary threats:
1.  **Pollution Attacks**: Malicious actors flooding the repo with fake or blocked proxies to dilute the pool.
2.  **Honeypots**: State actors deploying logging nodes to track users.
3.  **Takedowns**: Hosting providers removing the repo due to abuse reports.

## Mitigation Strategies

### 1. Pollution Defense (Anomaly Detection)
We use statistical analysis to detect pollution.
*   **Subnet Analysis**: Spammers rarely have diverse IPs. They spin up 100 containers on one Vultr/DigitalOcean droplet. If we see >90% of a batch coming from one /24 subnet, we drop it.
*   **Sequential Ports**: Proxies on `8001, 8002, 8003` are almost always a port scan or a single multi-user node. We deduplicate these aggressively.

### 2. Honeypot Detection
State actors often deploy "fake" open proxies to log traffic.
*   **Behavioral Analysis**: Our `HoneypotDetector` (`src/configstream/security/honeypot.py`) looks for:
    *   **Open Resolvers**: Proxies that resolve *internal* domains (like `intranet.corp`).
    *   **Echo Servers**: Proxies that return the request body exactly as sent (blind reflection).
    *   **Odd Headers**: Identifying headers injected by surveillance boxes (e.g., `X-Powered-By: GFW`).
*   **Action**: If detected, the proxy is flagged `risk:honeypot` and removed from the public pool.

### 3. Proxy Washing (IP Reputation)
Many "free" proxies are on IPs that are flagged by Cloudflare, Google, or other major providers. They connect, but they get CAPTCHAs or 403s.
*   **Concept**: We use the `ProxyWasher` (`src/configstream/intelligence/washer.py`).
*   **Mechanism**:
    *   `User -> [Dirty Proxy] -> [WARP Interface] -> Target`
*   **Implementation**:
    *   We generate a complex **Sing-box** configuration chain.
    *   The "Dirty Proxy" is the `outbound`.
    *   The `WARP` WireGuard tunnel is a second `outbound`.
    *   A `route` rule sends traffic from the Proxy outbound *into* the WARP outbound.
    *   The user gets a clean Cloudflare IP.
*   **Deterministic Key Assignment**: We map the Proxy ID to a specific WARP key using MD5, ensuring the same proxy always gets the same "Identity" (WARP key), preventing session churn.

### 4. TLS Fingerprinting (uTLS)
Standard Python `requests` or `ssl` libraries have a very distinct TLS fingerprint (JA3). Firewalls block this immediately.
*   **Solution**: We use **uTLS** (in our Go sidecar).
*   **Randomization**: We randomize the Client Hello packet to mimic:
    *   Chrome 120
    *   Firefox 118
    *   Safari 17
*   **Result**: We can successfully test and connect to proxies that block non-browser traffic.

### 5. Intranet Bridge
Some proxies are located inside restrictive domestic networks (e.g., Iran, China) and cannot reach the global internet directly, but *can* reach other domestic servers.
*   **Mechanism**: We chain these "Intranet" proxies through a "Bridge" proxy (a domestic server with international access, or a relay).
*   **Routing**: We create specific routing rules in `singbox.json` to tunnel traffic intelligently.

## Secrets Management

*   **No API Keys in Code**: We use GitHub Secrets.
*   **Gitleaks**: We run `gitleaks` in CI to catch accidental commits.
*   **Sanitization**: The pipeline strips `user`, `pass`, and `uuid` from logs. We only log the `hash(proxy)` for debugging.

## VirusTotal Integration

We cross-reference proxy IPs with VirusTotal's database.
*   **Metric**: "Malicious Votes".
*   **Threshold**: If > 3 vendors flag an IP as malware/botnet, we drop it.
*   **Caching**: We cache VT results for 7 days to respect API limits.
