# Laboratory Page

The **Laboratory** (`lab.html`) is ConfigStream's interactive chain-builder — a 5-step walkthrough that lets users construct, test, and export custom proxy chains directly in the browser.

---

## Overview

The Lab provides a guided workflow for advanced users who want to build censorship-resistant proxy chains. It supports parsing proxy URIs, discovering clean Cloudflare IPs, building chains with multiple strategies, live-testing them, and exporting to all major client formats.

**URL**: `/lab.html`

---

## 5-Step Walkthrough

### Step 1 — Parse Proxy URI

Paste a proxy URI (VLESS, VMess, Trojan, Shadowsocks, Hysteria2, TUIC, WireGuard) and the Lab parses it into a structured configuration object. The parser validates the URI, extracts credentials, transport settings, TLS parameters, and displays the parsed result.

**Supported protocols**: VLESS, VMess, Trojan, Shadowsocks, Hysteria2, TUIC, WireGuard, SSH, SOCKS5, HTTP.

### Step 2 — Discover Clean IPs

Find clean Cloudflare IP addresses to use as intermediaries in the chain. Three discovery modes:

- **Auto** — Fetches IPs from the ConfigStream scanner API
- **Manual** — Enter known clean IPs directly
- **Local Scan** — Runs a browser-based scan to find working IPs in your region

### Step 3 — Build Chain

Select a chain-building strategy and configure evasion options:

| Strategy | Description |
|----------|-------------|
| **WARP** | Single Cloudflare WARP hop before the proxy |
| **Double WARP** | Two WARP hops for extra obfuscation |
| **TLS Fragment** | TLS fragmentation to evade DPI |
| **CDN Worker** | Route through a Cloudflare Worker endpoint |
| **Custom JSON** | Paste a raw sing-box outbound JSON object |

**Advanced evasion options** (available per strategy):
- **uTLS Fingerprint** — Mimic browser TLS fingerprints (Chrome, Firefox, Safari, Edge, etc.)
- **ALPN** — Application-Layer Protocol Negotiation settings
- **Multiplex** — Connection multiplexing (h2mux, smux, yamux) with optional padding
- **TLS Fragmentation** — Split TLS ClientHello to evade deep packet inspection

### Step 4 — Test Chain

Verify the built chain works before exporting:

- **Live API Test** — Sends the chain to the ConfigStream test endpoint for real connectivity verification
- **Manual Fallback** — Provides sing-box CLI instructions for local testing when the API is unavailable

### Step 5 — Export

Export the chain configuration to any supported format:

| Format | Description |
|--------|-------------|
| **Sing-Box JSON** | Native sing-box configuration with full outbound chain |
| **Clash YAML** | Clash Meta (Mihomo) compatible YAML with proxy groups |
| **Xray JSON** | V2Ray/Xray JSON configuration with transport and TLS |
| **Nekobox Link** | Shareable link for NekoBox import |
| **URI** | Standard proxy URI for clipboard sharing |
| **QR Code** | Scannable QR code for mobile import |
| **Python Script** | Standalone Python script that runs the chain |
| **Bash Script** | Shell script for Linux/macOS deployment |

---

## Technical Details

### Frontend Files

- **HTML**: `frontend/lab.html` — Page structure and inline styles
- **JavaScript**: `frontend/assets/js/lab.js` — All chain-builder logic, parsing, IP discovery, chain construction, testing, and export

### Offline Tools

For environments without browser access, ConfigStream provides CLI equivalents:

- **`tools/lab-scanner.py`** — Python diagnostic tool for IP scanning
- **`tools/lab-runner.sh`** — Bash script for running chains locally
- **`frontend/lab-offline.html`** — Standalone HTML file that works without a server

### Export Compatibility

All exports include full transport support:
- WebSocket, gRPC, HTTP/2, httpupgrade transports
- Reality TLS with public key and short ID
- uTLS fingerprinting for all supported browsers
- ALPN negotiation
- WireGuard native format (Xray `secretKey` + `peers[]`, Clash `private-key` + `peers`)

---

## Related Documentation

- [Frontend Architecture](06-frontend.md) — Overall frontend design
- [Censorship Evasion](../../CENSORSHIP_EVASION.md) — Evasion strategies and techniques
- [API Reference](08-api-reference.md) — Test endpoint and scanner API
