# Networking Glossary

### ISP (Internet Service Provider)
The entity providing your internet connection. In censorship contexts, the ISP implements the blocking/filtering.

### TCP / UDP
- **TCP**: Reliable, connection-oriented. Used by VMess, Trojan, VLESS (TCP/WS/gRPC).
- **UDP**: Connectionless, fast. Used by WireGuard, Hysteria (QUIC).

### TLS (Transport Layer Security)
Encrypts traffic. Most modern proxies (Trojan, VLESS-Reality) rely on TLS to look like normal web traffic.

### SNI (Server Name Indication)
A field in the TLS handshake that indicates the hostname you are connecting to. Censors inspect SNI to block websites.

### ALPN (Application-Layer Protocol Negotiation)
Extension of TLS. Tells the server which protocol to use (h2, http/1.1). Censors can fingerprint this.

### DPI (Deep Packet Inspection)
Technique used by firewalls to analyze the content of packets (headers, payload) to identify and block protocols.

### QUIC
A UDP-based transport protocol used by HTTP/3 and Hysteria. Encrypts the entire transport layer, hiding handshake details better than TCP+TLS.
