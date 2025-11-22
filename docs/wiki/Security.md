# Security Engineering

ConfigStream operates on a **Zero-Trust** model. We assume every public proxy is potentially malicious, broken, or surveilled until verified.

## 1. Active Countermeasures

### Honeypot Detection
Malicious actors often set up "Free VPN" servers that are actually honeypots designed to log traffic or attack the user.

*   **Passive Check (VirusTotal):** We query the IP against VirusTotal's threat intelligence API. If it's flagged as a known botnet or malware host, we discard it.
*   **Active Port Scanning:** We actively probe specific "Management Ports" on the proxy server (TCP 21/FTP, 22/SSH, 23/Telnet).
    *   *Logic:* A legitimate censorship-circumvention node (VLESS/Trojan) should **never** expose these insecure ports to the public. If they are open, it's likely a compromised VPS or a honeypot.

### Traffic Verification (The "Canary")
We don't just ping `google.com`. We perform a cryptographic handshake.
*   The tester attempts to establish a real TLS connection through the proxy.
*   If the proxy intercepts the TLS handshake (Man-in-the-Middle), the certificate validation fails, and the proxy is rejected.

## 2. Proxy Washing

**Problem:** Many clean, high-speed proxies are hosted on IPs that are blocked by Google, Netflix, or ChatGPT (403 Forbidden).
**Solution:** Proxy Washing.

We wrap these "Dirty" proxies in a **WireGuard Tunnel** using Cloudflare WARP.

*   **The Chain:** `User -> Dirty Proxy (Relay) -> WARP (Exit) -> Internet`
*   **Benefit:**
    1.  **Unblocking:** The final IP seen by websites is Cloudflare's clean IP.
    2.  **Security:** The "Dirty" proxy operator only sees encrypted WireGuard UDP packets. They cannot inspect the SNI or content.

This effectively turns "Trash" proxies into "Premium" private lines.

## 3. Anomaly Detection

To prevent "Supply Chain Poisoning" (a malicious source flooding our repo with 10,000 fake proxies), we use the `AnomalyDetector`.

*   **Subnet Floods:** If >90% of proxies in a batch come from the same `/24` subnet, we reject the entire batch.
*   **Z-Score Analysis:** We track the average "Yield" of a source. If a source normally provides 5 proxies but suddenly provides 5,000, it triggers an anomaly alert and is quarantined.
