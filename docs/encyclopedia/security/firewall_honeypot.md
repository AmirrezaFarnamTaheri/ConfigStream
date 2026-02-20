# Firewalls & Honeypots

## The Adversaries

### GFW (Great Firewall)
Uses advanced Deep Packet Inspection (DPI) to identify and block protocols.
- **Active Probing**: Sends crafted packets to suspected proxies to trigger a response.
- **DPI**: Analyzes TLS handshakes (SNI, ALPN, Fingerprint).

### Russia / Iran
Focus heavily on blocking known VPN protocols (WireGuard, OpenVPN) and throttling UDP (affecting QUIC/Hysteria).

## ConfigStream Defenses

### 1. Honeypot Detection
ConfigStream tests proxies against a known "Canary" URL. If the proxy redirects to a block page or returns a fake response, it is flagged as a **HONEYPOT** or **DIRTY_IP** and filtered out of "Clean" lists.

### 2. Evasion Features
- **uTLS**: Randomizes TLS fingerprints to mimic Chrome/Firefox.
- **Padding**: Adds random data to hide packet size patterns.
- **Fragmentation**: Splits TLS ClientHello packets to evade SNI blocking.

### 3. Fail-Safe
If a proxy behaves suspiciously (e.g. successful TCP connection but timeouts on data), it is treated as a potential probe/honeypot.
