# Security & Obfuscation Concepts

## Steganographic (Steganography)
From Greek *steganos* (covered) and *graphein* (writing). Unlike cryptography, which hides the *meaning* of a message, steganography hides the *existence* of the message.
*   **In ConfigStream:** We embed encrypted JSON configurations inside the Least Significant Bits (LSB) of JPEG/PNG images.
*   **Why?** A network administrator seeing you download `config.json` might block it. Seeing you download `cute_cat.jpg` is usually ignored.
*   **Transport:** The image acts as a "carrier" for the data.
*   **HTML Smuggling:** A related technique where configs are hidden inside innocent-looking HTML pages (e.g., in a `<meta>` tag), decoded by JavaScript on the client side. ConfigStream implements this in `tools/html_smuggler.py`.

## VirusTotal Integration
VirusTotal is a service that analyzes files and URLs using over 70 antivirus scanners.
*   **Role in ConfigStream:** Before including a proxy in our final list, we (optionally) check its IP or domain against VirusTotal's API.
*   **Safety:** This ensures we aren't distributing proxies hosted on known malware command-and-control (C2) servers, protecting users from malicious endpoints.
*   **FireHol Integration:** In addition to VirusTotal, ConfigStream integrates FireHol Level 1 blocklists — curated lists of known malicious IPs (botnets, spam, C2 servers). Any proxy matching these lists is dropped before it reaches the user.

## Handshake
The initial negotiation phase of a network connection.
*   **The Vulnerability:** Censors (like the GFW) heavily inspect handshakes because they must be unencrypted (or partially unencrypted) to establish keys.
*   **WireGuard Handshake:** Very distinct 148-byte packet. Easy to fingerprint and block. This is why raw WireGuard (WARP) needs clean IPs — the handshake is identifiable but Cloudflare IPs are too costly to block.
*   **Shadowsocks Handshake:** Originally random-looking, but machine learning can now detect its entropy profile. SS2022 improves this but is still detectable by advanced DPI.
*   **Reality Handshake:** Indistinguishable from a standard TLS handshake with a legitimate website. The gold standard for stealth.
*   **Trojan Handshake:** A real TLS handshake with a valid certificate. If the password is wrong, the server serves a real website. Censors cannot distinguish it from normal HTTPS browsing.

## Active Probing
A technique where the censor doesn't just passively observe traffic — it actively sends packets to suspected proxy servers to confirm they are proxies.
*   **How it works:** When the GFW/censor sees suspicious traffic (e.g., entropy pattern matching Shadowsocks), it records the destination IP:port. Minutes later, it sends its own probe packets mimicking a client handshake. If the server responds like a proxy, the IP is blacklisted.
*   **Replay Attack:** The censor records the first few bytes of a real client connection and replays them to the server. If the server responds identically, it's confirmed as a proxy.
*   **ConfigStream Defense:** We prioritize protocols resistant to active probing:
    *   **Reality:** Probers see a real website, not a proxy.
    *   **Trojan:** Wrong password → fallback to legitimate web server.
    *   **Worker Masquerading:** Root path serves a real website (e.g., kernel.org); proxy tunnel only accessible via secret path.

## Traffic Analysis
Inferring information about encrypted communications by analyzing metadata (not content).
*   **Packet Size Analysis:** Different activities produce different packet size distributions. Video streaming has large, regular packets. Web browsing has variable sizes. VPN tunnels often have uniform MTU-sized packets.
*   **Timing Analysis:** The pattern of when packets are sent can reveal what you're doing, even if the content is encrypted.
*   **Volume Analysis:** A sustained high-bandwidth connection to a single IP is suspicious if that IP is a known proxy endpoint.
*   **ConfigStream Countermeasures:**
    *   **Multiplexing with Padding:** Randomizes packet sizes within multiplexed streams.
    *   **ALPN Rotation:** Varies protocol negotiation to avoid fingerprinting.
    *   **uTLS Fingerprinting:** Makes TLS handshakes look like specific browser versions.

## Circuit Breaker Pattern
A software resilience pattern borrowed from electrical engineering.
*   **Analogy:** Like a circuit breaker in your house that trips when there's a power surge, a software circuit breaker "trips" when a service fails repeatedly.
*   **In ConfigStream:**
    *   **Closed (Normal):** Requests flow through to the source/proxy.
    *   **Open (Tripped):** After N consecutive failures, the circuit breaker stops sending requests for a cooldown period. This prevents hammering dead hosts and wasting pipeline time.
    *   **Half-Open (Testing):** After cooldown, a single test request is sent. If it succeeds, the breaker closes (resumes). If it fails, it stays open.
*   **Usage:** Applied to source fetching (if a GitHub repo is down, stop retrying for the rest of the run) and proxy testing (if an IP fails 3 times, skip it).

## Adaptive Timeout
A dynamic timeout strategy that learns from historical latency.
*   **Problem:** A fixed 10-second timeout wastes time on fast sources (which respond in 500ms) and is too aggressive for slow but valid sources (which need 8s).
*   **Solution:** ConfigStream tracks the average response time for each source. If a source usually responds in 1s, we set its timeout to 3s (3× average). If it takes 5s today, we know something is wrong and cut it.
*   **Implementation:** `AdaptiveTimeout` class in the intelligence layer, using exponential moving average of latency.
