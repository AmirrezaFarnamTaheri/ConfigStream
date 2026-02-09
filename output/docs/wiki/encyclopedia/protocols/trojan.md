# Trojan Protocol

## Overview
Trojan is a protocol designed to bypass the GFW by impersonating HTTPS (TLS) traffic. Unlike VMess or Shadowsocks which use custom encryption protocols, Trojan tunnels traffic over standard TLS, making it look exactly like a user visiting a website. It is one of the most effective stealth protocols and a first-class citizen in ConfigStream.

## Mechanism
1.  **TLS Handshake:** The client connects to the server on port 443 and performs a real, valid TLS handshake. The censor sees a normal HTTPS connection to a legitimate-looking domain.
2.  **Authentication:** The first packet inside the encrypted TLS tunnel contains a SHA-224 hash of the password, followed by `\r\n`, the target address, and the payload.
3.  **Routing:**
    *   **Success:** If the password hash matches, traffic is proxied to the requested destination.
    *   **Failure:** If the password is wrong (or active probing is detected), the server transparently proxies the connection to a **fallback web server** (e.g., Nginx serving a static page, or a real website like `www.example.com`). This fallback behavior is the key to Trojan's stealth — active probers see a real website.

## The Fallback Mechanism (Deep Dive)
The fallback is what makes Trojan exceptional against active probing:
*   **To the censor:** Connecting to the Trojan server without the correct password shows a legitimate website (blog, corporate page, etc.). There is no way to distinguish it from a normal web server.
*   **Nginx/Caddy Integration:** Trojan servers typically run behind Nginx or Caddy with a valid Let's Encrypt certificate. The web server handles legitimate HTTPS traffic while Trojan handles authenticated proxy traffic on the same port.
*   **Multi-Fallback:** Advanced setups (Xray, Trojan-Go) support multiple fallback paths based on the ALPN protocol, path, or SNI — allowing different services to coexist on port 443.

## Variants

### Original Trojan
*   **Transport:** TCP only (with TLS).
*   **Authentication:** SHA-224(password) in first packet.
*   **Limitations:** No WebSocket or gRPC transport.

### Trojan-Go
*   **Enhanced Version:** Adds WebSocket transport, multiplexing, and CDN compatibility.
*   **WebSocket:** Allows Trojan to work behind CDNs (like Cloudflare) that don't support raw TCP.
*   **Multiplexing:** Reduces connection overhead by sharing a single TCP connection for multiple streams.

### Xray Trojan
*   **XTLS Integration:** Xray's Trojan implementation supports XTLS (a TLS optimization that avoids double encryption) and XTLS-Vision (which makes the TLS flow look more natural).
*   **Fallback Chains:** Supports complex fallback configurations based on ALPN, path, and SNI.

## Pros & Cons
*   **Pros:**
    *   Highly effective against DPI and active probing (fallback to real website).
    *   Lightweight — minimal overhead over standard TLS.
    *   Works with CDNs via WebSocket transport (Trojan-Go, Xray).
    *   Stealth score: 9/10 in ConfigStream's protocol intelligence matrix.
*   **Cons:**
    *   Requires a domain name and valid TLS certificate for maximum stealth.
    *   Self-signed certificates reduce stealth (the censor can detect non-CA certificates).
    *   Password-based authentication means a compromised password exposes the server.

## ConfigStream Parsing

### URI Format
```
trojan://PASSWORD@HOST:PORT?security=tls&sni=DOMAIN&type=tcp#REMARK
```

### Parsing Logic
1.  Extract password from the userinfo portion of the URI.
2.  Parse query parameters for `security`, `sni`, `type` (transport), `host`, `path`.
3.  If `security=tls` or absent, enable TLS. If `security=reality`, parse Reality fields.
4.  If transport `type=ws`, extract WebSocket path and host header.
5.  **Credential Recovery:** If password is empty, check query parameters as fallback before dropping.

### Validation Rules
*   Password must not be empty (mandatory field).
*   Host must be a valid hostname or IP.
*   Port must be 1-65535 (typically 443).

## Configuration Structure (Sing-box)
```json
{
  "type": "trojan",
  "tag": "proxy-trojan",
  "server": "example.com",
  "server_port": 443,
  "password": "my-password",
  "tls": {
    "enabled": true,
    "server_name": "example.com",
    "utls": {
      "enabled": true,
      "fingerprint": "chrome"
    }
  }
}
```

### With WebSocket Transport (CDN-compatible)
```json
{
  "type": "trojan",
  "tag": "proxy-trojan-ws",
  "server": "cdn-ip-or-domain.com",
  "server_port": 443,
  "password": "my-password",
  "tls": {
    "enabled": true,
    "server_name": "your-domain.com"
  },
  "transport": {
    "type": "ws",
    "path": "/trojan-ws",
    "headers": { "Host": "your-domain.com" }
  }
}
```

## Client Compatibility
| Client | Support | Notes |
| :--- | :--- | :--- |
| Sing-box | Full | TCP, WS, gRPC, Reality |
| Clash Meta | Full | TCP, WS, gRPC |
| V2RayN/NG | Full | All transports |
| Shadowrocket | Full | All transports |
| Surge | Partial | TCP only |
| Loon | Partial | TCP, WS |
