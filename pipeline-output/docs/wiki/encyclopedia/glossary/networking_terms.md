# Networking & Cryptography Fundamentals

## Infrastructure

### ISP (Internet Service Provider)
The company that provides you with access to the Internet (e.g., Comcast, AT&T, Deutsche Telekom).
*   **Role:** Your ISP sees every packet you send. If the packet is unencrypted (HTTP), they see the content. If encrypted (HTTPS), they see the destination IP and often the SNI (domain name).
*   **Throttling:** ISPs can slow down specific types of traffic (e.g., torrents or VPNs) based on patterns.

### Route (Routing)
The path data takes from your device to the destination.
*   **Hops:** Data jumps from router to router.
*   **Optimized Route:** A "better" route has fewer hops or less congested links. ConfigStream's "Smart Routing" tries to send traffic through the fastest available path (e.g., using a Clean IP that has good peering with your ISP).

## Protocols & Transport

### UDP (User Datagram Protocol)
A connectionless protocol. Unlike TCP, it doesn't guarantee delivery or order.
*   **Speed:** Faster than TCP because there is no handshake.
*   **Usage:** Video streaming, Gaming, DNS, and **QUIC** (Hysteria2/TUIC).
*   **Blocking:** Many firewalls aggressively block or throttle UDP because it's harder to inspect statefully.

### TCP (Transmission Control Protocol)
A connection-oriented protocol. It guarantees data arrives in order and without errors.
*   **Handshake:** Requires a 3-way handshake (SYN, SYN-ACK, ACK) before data flows.
*   **Reliability:** The foundation of the web (HTTP/1.1, HTTP/2).

## Security Concepts

### Handshake
The initial negotiation between a client and server to establish a connection.
*   **TCP Handshake:** "Hello, are you there?" -> "Yes, I am." -> "Great, let's talk."
*   **TLS Handshake:** "Let's speak securely. Here are my supported ciphers." -> "Okay, let's use AES-256. Here is my certificate."
*   **Vulnerability:** The handshake is the most vulnerable part of a connection. Censors look for specific byte patterns in the first few packets to identify VPNs (e.g., the WireGuard handshake is very distinct).

### TLS (Transport Layer Security)
The successor to SSL. It encrypts traffic so that no one in the middle (ISP, Hacker) can read it.
*   **Encryption:** Scrambles the payload.
*   **Authentication:** Verifies the server is who it claims to be (using Certificates).

### SNI (Server Name Indication)
An extension to TLS. When you connect to a server that hosts multiple websites (virtual hosting), your client sends the hostname (e.g., `google.com`) in **cleartext** during the handshake so the server knows which certificate to provide.
*   **Privacy Leak:** This allows ISPs and Censors to see exactly which website you are visiting, even if the content is encrypted.
*   **ESNI / ECH:** Encrypted SNI / Encrypted Client Hello. New standards to fix this leak, but heavily blocked by censors like the GFW.

## Obfuscation Techniques

### Padding
Adding random, meaningless data (junk) to a packet to change its size.
*   **Purpose:** Resists **Traffic Analysis**. If every login packet is exactly 50 bytes, a censor can identify it. If we pad it to be random (50-200 bytes), it blends in with regular browsing.

### Noise
Random data sent to confuse a passive observer or active prober.
*   **ConfigStream Usage:** Some parsers reject input if the "Noise Ratio" (non-printable characters) is too high, assuming it's garbage. Conversely, obfuscation protocols add noise to look like static.
