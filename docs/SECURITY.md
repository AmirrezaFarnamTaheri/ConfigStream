# Security Architecture

ConfigStream implements a "Defense in Depth" strategy to protect users from malicious proxies.

## 1. The Signed Honeypot

Malicious proxies often "fake" a successful connection by returning 200 OK to every request, or they inject ads/malware.

**The Solution:**
We deploy a "Canary" Cloudflare Worker (`tools/bot/worker.js`).

1.  **Sign:** The worker has a `SECRET_KEY`. It exposes an endpoint `/canary/sign?token=RANDOM`.
2.  **Verify:** The Go Tester generates a random token, connects *through* the proxy to the worker, and requests a signature.
3.  **Validate:** The Tester calculates `HMAC(token, SECRET_KEY)` locally. If it matches the worker's response, the proxy is genuine. If it mismatches or returns garbage, the proxy is **BANNED**.

## 2. Protocol Washing (The Laundromat)

Public HTTP/SOCKS5 proxies are insecure (plaintext).
ConfigStream **washes** them by chaining them:

`User -> [Insecure Proxy] -> [WireGuard/TLS Relay] -> Internet`

*   **User to Proxy:** The insecure proxy only sees an encrypted WireGuard/TLS stream.
*   **Proxy to Internet:** The secure relay handles the exit.
*   **Result:** The insecure proxy cannot see user data, and the user gets a clean IP.

## 3. IP Reputation

We verify resolved IPs against:
*   **FireHol Level 1:** Known attacker lists.
*   **Subnet Flood:** Detecting if a single provider is spamming thousands of IPs.
