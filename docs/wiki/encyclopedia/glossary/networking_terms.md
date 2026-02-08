# Networking & Cryptography Fundamentals

## Infrastructure

### ISP (Internet Service Provider)
The company that provides you with access to the Internet (e.g., Comcast, AT&T, Deutsche Telekom, MCI/Irancell in Iran).
*   **Role:** Your ISP sees every packet you send. If the packet is unencrypted (HTTP), they see the content. If encrypted (HTTPS), they see the destination IP and often the SNI (domain name).
*   **Throttling:** ISPs can slow down specific types of traffic (e.g., torrents or VPNs) based on patterns. This is sometimes called "traffic shaping."
*   **DPI Appliances:** Many ISPs deploy Deep Packet Inspection hardware inline. These boxes examine packet headers, payload patterns, and statistical features to classify and block traffic in real-time.

### Route (Routing)
The path data takes from your device to the destination.
*   **Hops:** Data jumps from router to router. Use `traceroute` (Linux/Mac) or `tracert` (Windows) to see the path.
*   **Optimized Route:** A "better" route has fewer hops or less congested links. ConfigStream's "Smart Routing" tries to send traffic through the fastest available path (e.g., using a Clean IP that has good peering with your ISP).
*   **BGP (Border Gateway Protocol):** The protocol that ISPs use to exchange routing information. Censors can manipulate BGP to blackhole (silently drop) traffic to specific IP ranges.

### CDN (Content Delivery Network)
A globally distributed network of servers that caches and delivers content closer to users.
*   **Examples:** Cloudflare, Fastly, Akamai, Amazon CloudFront.
*   **Censorship Relevance:** CDNs serve a huge portion of the internet. Blocking a CDN's IP range causes **collateral damage** — breaking thousands of legitimate websites. This is why Cloudflare WARP is effective: blocking it breaks too many other services.
*   **Domain Fronting:** A technique where you connect to a CDN's IP address (which is allowed) but send a different hostname in the HTTP `Host` header (which is proxied to your actual destination). TLS SNI shows the CDN domain, hiding the real destination from the censor.

## Protocols & Transport

### UDP (User Datagram Protocol)
A connectionless protocol. Unlike TCP, it doesn't guarantee delivery or order.
*   **Speed:** Faster than TCP because there is no handshake.
*   **Usage:** Video streaming, Gaming, DNS, and **QUIC** (Hysteria2/TUIC).
*   **Blocking:** Many firewalls aggressively block or throttle UDP because it's harder to inspect statefully. Iran blocks most non-DNS UDP traffic during shutdowns.

### TCP (Transmission Control Protocol)
A connection-oriented protocol. It guarantees data arrives in order and without errors.
*   **Handshake:** Requires a 3-way handshake (SYN, SYN-ACK, ACK) before data flows.
*   **Reliability:** The foundation of the web (HTTP/1.1, HTTP/2).
*   **RST Injection:** A common censorship technique where the firewall sends a fake TCP RST (reset) packet to both sides, killing the connection. The client and server both think the other side closed the connection.

### QUIC (Quick UDP Internet Connections)
A modern transport protocol built on UDP, developed by Google and standardized as HTTP/3.
*   **Encryption:** QUIC encrypts the entire transport layer, including headers. Censors can see it's QUIC but cannot inspect the contents.
*   **Multiplexing:** Multiple streams share one connection without head-of-line blocking.
*   **Usage in Circumvention:** Hysteria2 and TUIC are built on QUIC. They exploit its speed and encryption but are vulnerable to blanket UDP blocking.
*   **Fingerprinting:** QUIC's initial handshake has identifiable patterns. Some censors can detect and block specific QUIC-based protocols.

### HTTP CONNECT Tunnel
An HTTP method that establishes a TCP tunnel through an HTTP proxy.
*   **Mechanism:** The client sends `CONNECT target:port HTTP/1.1` to the proxy. If the proxy approves, it creates a raw TCP tunnel to the target. All subsequent data passes through unmodified.
*   **Usage:** This is how browsers use HTTP proxies for HTTPS sites. It's also how many circumvention tools chain through corporate proxies.
*   **Relevance:** If you find an HTTP proxy on your LAN (e.g., a corporate proxy at `10.0.0.1:3128`), you can CONNECT-tunnel through it to reach external proxies or WARP endpoints.

### SOCKS5 (Socket Secure v5)
A general-purpose proxy protocol that supports any TCP or UDP traffic.
*   **Mechanism:** The client connects to the SOCKS proxy, authenticates (optional), then requests a connection to a target. The proxy relays all data.
*   **Advantage over HTTP proxy:** SOCKS5 can proxy UDP traffic (important for QUIC/DNS), not just TCP.
*   **Usage:** Tools like Psiphon, Tor, and V2Ray often expose a local SOCKS5 port (e.g., `127.0.0.1:1080`). You can chain other proxies through this port.

## Security Concepts

### Handshake
The initial negotiation between a client and server to establish a connection.
*   **TCP Handshake:** "Hello, are you there?" -> "Yes, I am." -> "Great, let's talk." (SYN → SYN-ACK → ACK)
*   **TLS Handshake:** "Let's speak securely. Here are my supported ciphers." -> "Okay, let's use AES-256. Here is my certificate." (ClientHello → ServerHello → Certificate → Finished)
*   **Vulnerability:** The handshake is the most vulnerable part of a connection. Censors look for specific byte patterns in the first few packets to identify VPNs (e.g., the WireGuard handshake is a very distinct 148-byte packet).

### TLS (Transport Layer Security)
The successor to SSL. It encrypts traffic so that no one in the middle (ISP, Hacker) can read it.
*   **Encryption:** Scrambles the payload using symmetric ciphers (AES-GCM, ChaCha20-Poly1305).
*   **Authentication:** Verifies the server is who it claims to be (using X.509 Certificates signed by Certificate Authorities).
*   **Versions:** TLS 1.2 is the minimum acceptable version. TLS 1.3 is preferred — it encrypts more of the handshake and is faster (1-RTT).
*   **uTLS:** A library that allows custom TLS fingerprints. Instead of your connection looking like "Go client" (which censors block), it looks like "Chrome 120" or "Firefox 121." ConfigStream rotates uTLS fingerprints across proxies.

### SNI (Server Name Indication)
An extension to TLS. When you connect to a server that hosts multiple websites (virtual hosting), your client sends the hostname (e.g., `google.com`) in **cleartext** during the TLS ClientHello so the server knows which certificate to provide.
*   **Privacy Leak:** This allows ISPs and Censors to see exactly which website you are visiting, even if the content is encrypted.
*   **SNI Blocking:** The censor inspects the SNI field and drops connections to blocked domains. This is the primary censorship mechanism in Iran, Russia, and China for HTTPS traffic.
*   **ESNI / ECH (Encrypted Client Hello):** New standards that encrypt the SNI field inside the TLS handshake. ECH uses a public key published in DNS to encrypt the entire ClientHello. Currently blocked in China (they block connections that use ECH) but may work in other regions.

### DPI (Deep Packet Inspection)
Hardware or software that examines the content of network packets beyond just headers.
*   **Stateless DPI:** Looks at individual packets in isolation. Can be defeated by **TLS fragmentation** (splitting the ClientHello across multiple TCP segments so no single packet contains the full SNI).
*   **Stateful DPI:** Reassembles TCP streams and inspects the full conversation. Much harder to evade. Requires protocol-level obfuscation (Reality, Trojan, or traffic multiplexing with padding).
*   **ML-Based DPI:** Uses machine learning to classify traffic by statistical features (packet size distribution, timing, entropy). Can detect Shadowsocks even though it looks "random" — because randomness itself is a pattern.

## Obfuscation Techniques

### Padding
Adding random, meaningless data (junk) to a packet to change its size.
*   **Purpose:** Resists **Traffic Analysis**. If every login packet is exactly 50 bytes, a censor can identify it. If we pad it to be random (50-200 bytes), it blends in with regular browsing.
*   **Implementation:** ConfigStream enables multiplexing with padding (h2mux) in aggressive evasion mode, randomizing packet sizes.

### Noise
Random data sent to confuse a passive observer or active prober.
*   **ConfigStream Usage:** Some parsers reject input if the "Noise Ratio" (non-printable characters) is too high, assuming it's garbage. Conversely, obfuscation protocols add noise to look like static.

### TLS Fragmentation
Splitting the TLS ClientHello message across multiple TCP segments.
*   **Purpose:** Stateless DPI boxes inspect individual packets. If the SNI field is split across two packets, the DPI cannot read it and lets the connection through.
*   **Parameters:** Fragment size (e.g., 10-30 bytes) and delay between fragments (e.g., 5-10ms).
*   **Limitation:** Ineffective against stateful DPI that reassembles the stream before inspection.

### Domain Fronting
Using one domain in the TLS SNI (visible to the censor) while sending a different domain in the HTTP Host header (visible only to the CDN).
*   **Example:** SNI says `allowed-site.com` (censor sees this and allows it). Host header says `blocked-proxy.com` (the CDN routes to this).
*   **Status:** Google and Amazon disabled domain fronting on their CDNs. Cloudflare still allows it in some configurations. ConfigStream's CDN Worker strategy is a modern, sanctioned alternative.

### Reality Protocol
A protocol developed by XTLS/Xray that makes proxy traffic indistinguishable from visiting a real website.
*   **Mechanism:** The server presents a real, valid TLS certificate for a legitimate domain (e.g., `www.microsoft.com`). Active probers that connect without the correct credentials are transparently proxied to the real website.
*   **Advantage:** No need for your own domain or certificate. The censor cannot distinguish Reality traffic from normal HTTPS browsing.
*   **ConfigStream Support:** VLESS+Reality is a first-class citizen in ConfigStream's parsing and output pipeline.
