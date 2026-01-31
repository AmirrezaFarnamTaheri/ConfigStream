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

Current implementation focusses on **passive** intelligence only:

*   **VirusTotal Integration**: Our honeypot guard (`src/configstream/security/honeypot.py`) uses `check_ip_reputation()` to check whether an IP has been flagged as malicious.
    *   If VirusTotal reports `malicious > 0`, the proxy is flagged and removed from the pool.
    *   If the `VT_API_KEY` is missing, we **log a warning** and fail open (no blocking), so operators are aware that honeypot reputation checks are effectively disabled.
*   **No Active Scanning**: Behavioral checks like open resolvers, echo servers, and header fingerprinting are **documented but not enabled** in production to respect a strict “Zero Abuse” policy and avoid port‑scan behaviour.
    *   The `check_common_honeypot_ports()` and `check_traffic_interception()` helpers are intentionally stubs.
    *   Future work may add passive heuristics here (e.g. offline logs analysis) without probing the remote hosts.

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
*   **Deterministic Key Assignment**: We map the Proxy ID to a specific WARP key using a hash (now based on SHA‑256) so that the same proxy always gets the same "Identity" (WARP key), preventing session churn.
*   **Candidate Selection**: When a WARP key pool is configured, we wash **all working proxies** (not only those tagged `dirty_ip`/`insecure`) to ensure that untagged but risky nodes still benefit from a clean egress IP.

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
*   **Failure Mode**: If the API key is not configured or the API fails, we log a **warning** and fail open for that check only (the proxy may still be rejected by other validators such as blocklists or DNS rules).

## Anomaly Detection & Fail‑Open Policy

The `AnomalyDetector` (`src/configstream/anomaly.py`) protects against **pollution attacks** by modelling per‑source history and identifying massive spikes or drops.

*   For established sources, Isolation Forest / Z‑score heuristics are used to detect outliers in batch size.
*   For new or small sources, simple heuristics guard against “sudden massive yield”.
*   **Failure Mode**: If the anomaly database is temporarily unavailable (e.g. SQLite error), we now **fail open**:
    *   The source is **allowed** for this run.
    *   An error is logged with `DB Error (Fail Open)` so operators can fix the underlying storage problem.
    *   This prevents a transient DB issue from blocking **all** upstreams and silently collapsing the pipeline.

