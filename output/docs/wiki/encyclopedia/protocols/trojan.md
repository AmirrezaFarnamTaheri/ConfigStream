# Trojan Protocol

## Overview
Trojan is a protocol designed to bypass the GFW by impersonating HTTPS (TLS) traffic. Unlike VMess or Shadowsocks which use custom encryption protocols, Trojan tunnels traffic over standard TLS, making it look exactly like a user visiting a website.

## Mechanism
1.  **TLS Handshake:** The client connects to the server on port 443.
2.  **Authentication:** The first packet inside the TLS tunnel contains the password (hash).
3.  **Routing:**
    *   **Success:** If the password is correct, traffic is proxied.
    *   **Failure:** If the password is wrong (or active probing is detected), the server redirects the connection to a real web server (e.g., Nginx serving a static page). This "fallback" behavior makes it extremely hard to distinguish from a normal web server.

## Pros & Cons
*   **Pros:** Highly effective against simple whitelist/blacklist firewalls; lightweight.
*   **Cons:** Requires a domain name and valid certificate (though self-signed can work with `insecure` mode, it reduces stealth).

## Configuration Structure
```json
{
  "type": "trojan",
  "server": "example.com",
  "server_port": 443,
  "password": "my-password",
  "tls": {
    "enabled": true,
    "server_name": "example.com"
  }
}
```
