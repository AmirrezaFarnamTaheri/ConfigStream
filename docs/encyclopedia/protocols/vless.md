# VLESS Protocol

## Overview
VLESS is a lightweight, stateless proxy protocol developed by the XTLS/Xray project. Unlike VMess, VLESS does not perform its own encryption — it relies entirely on the underlying transport layer (TLS or Reality) for security. This makes it faster and simpler than VMess while being equally stealthy.

VLESS is a first-class citizen in ConfigStream and consistently ranks among the most popular protocols in the output.

## How It Works

1.  **Connection**: The client connects to the server over TLS (or Reality).
2.  **Authentication**: The first payload inside the encrypted tunnel contains a UUID (16 bytes) that identifies the user. No additional encryption is applied — the TLS layer handles confidentiality.
3.  **Proxying**: After authentication, the server proxies traffic to the requested destination. The protocol overhead is minimal (just the UUID header).

### Why No Built-In Encryption?
VMess encrypts traffic twice: once at the protocol level (AES-128-GCM or ChaCha20-Poly1305) and once at the transport level (TLS). This double encryption wastes CPU and adds latency. VLESS eliminates the protocol-level encryption entirely, trusting TLS to do its job. The result is lower CPU usage and faster throughput.

## VLESS + Reality (The Gold Standard)

Reality is a TLS camouflage system that makes VLESS connections indistinguishable from normal HTTPS browsing.

### How Reality Works
1.  **Server Setup**: The server is configured with a "target" domain (e.g., `www.microsoft.com`) and generates a Reality keypair.
2.  **Client Connection**: The client connects and presents a TLS ClientHello that looks identical to a connection to the target domain.
3.  **Server Response**: If the client provides the correct Reality credentials (`pbk`, `sid`), the server accepts the proxy connection. If not, the server transparently proxies the connection to the *real* target domain.
4.  **Active Probe Resistance**: A censor probing the server sees a legitimate Microsoft website. There is no way to distinguish it from a real web server without the Reality private key.

### Required Fields
*   `pbk` — Server's Reality public key (base64).
*   `sid` — Short ID (hex string, typically 8 characters).
*   `sni` — The domain being mimicked (e.g., `www.microsoft.com`).
*   `fp` — Browser fingerprint for uTLS (e.g., `chrome`, `firefox`).

### Advantages Over Standard TLS
*   **No Domain Required**: You don't need to own a domain or obtain a certificate.
*   **No Certificate Expiry**: Reality doesn't use Let's Encrypt certificates that need renewal.
*   **Perfect Camouflage**: Active probers see a real website, not a proxy.

## URI Format

```
vless://UUID@HOST:PORT?security=tls&sni=DOMAIN&type=ws&host=CDN&path=/path&fp=chrome#REMARK
```

### Reality Variant
```
vless://UUID@HOST:PORT?security=reality&pbk=PUBLIC_KEY&sid=SHORT_ID&sni=www.microsoft.com&type=tcp&fp=chrome#REMARK
```

## Transport Options

| Transport | Field | Use Case |
| :--- | :--- | :--- |
| **TCP** | `type=tcp` | Direct connection. Lowest latency. |
| **WebSocket** | `type=ws`, `path`, `host` | CDN-compatible (Cloudflare, etc.). |
| **gRPC** | `type=grpc`, `serviceName` | Multiplexed, CDN-compatible. |
| **HTTP/2** | `type=h2`, `path`, `host` | Multiplexed over TLS. |
| **Split-HTTP** | `type=splithttp` | Experimental. Splits requests across multiple HTTP connections. |

## ConfigStream Parsing

1.  Parse UUID from the userinfo portion of the URI.
2.  Extract query parameters: `security`, `sni`, `type`, `host`, `path`, `fp`, `pbk`, `sid`, `flow`.
3.  **Credential Recovery**: If UUID is empty in the userinfo, check query parameters as fallback before dropping.
4.  **Reality Validation**: If `security=reality`, require `pbk` and `sid`. Drop if missing.
5.  **Flow Handling**: `flow=xtls-rprx-vision` is preserved for XTLS-Vision support.

## Sing-box Configuration

### Standard VLESS + TLS
```json
{
  "type": "vless",
  "tag": "proxy-vless",
  "server": "example.com",
  "server_port": 443,
  "uuid": "your-uuid-here",
  "tls": {
    "enabled": true,
    "server_name": "example.com",
    "utls": { "enabled": true, "fingerprint": "chrome" }
  }
}
```

### VLESS + Reality
```json
{
  "type": "vless",
  "tag": "proxy-vless-reality",
  "server": "1.2.3.4",
  "server_port": 443,
  "uuid": "your-uuid-here",
  "flow": "xtls-rprx-vision",
  "tls": {
    "enabled": true,
    "server_name": "www.microsoft.com",
    "reality": {
      "enabled": true,
      "public_key": "base64-public-key",
      "short_id": "abcd1234"
    },
    "utls": { "enabled": true, "fingerprint": "chrome" }
  }
}
```

### VLESS + WebSocket (CDN-Compatible)
```json
{
  "type": "vless",
  "tag": "proxy-vless-ws",
  "server": "cdn-ip.example.com",
  "server_port": 443,
  "uuid": "your-uuid-here",
  "tls": {
    "enabled": true,
    "server_name": "your-domain.com"
  },
  "transport": {
    "type": "ws",
    "path": "/vless-ws",
    "headers": { "Host": "your-domain.com" }
  }
}
```

## Protocol Intelligence Scores

| Metric | Score | Notes |
| :--- | :--- | :--- |
| **Stealth** | 10/10 | With Reality: indistinguishable from HTTPS. |
| **Speed** | 7/10 | No double encryption. Efficient. |
| **Reliability** | 8/10 | Stable, well-tested implementations. |
| **Penalty (km)** | 0 | No routing penalty in chain scoring. |

## Client Compatibility

| Client | Support | Notes |
| :--- | :--- | :--- |
| Sing-box | Full | TCP, WS, gRPC, H2, Reality, XTLS-Vision |
| Clash Meta | Full | TCP, WS, gRPC, Reality |
| V2RayN/NG | Full | All transports |
| Shadowrocket | Full | All transports |
| Surge | Partial | TCP, WS (no Reality) |
| Loon | Partial | TCP, WS |

## Related Documentation

*   **[VMess Protocol](vmess.md)** — VLESS's predecessor; heavier encryption but wider client support.
*   **[Trojan Protocol](trojan.md)** — Alternative stealth protocol using HTTPS mimicry instead of Reality.
*   **[Sing-box Configuration Guide](../tools/singbox_configuration_guide.md)** — How VLESS outbounds are structured in Sing-box JSON.
*   **[Networking Terms — TLS, SNI, DPI](../glossary/networking_terms.md)** — The concepts Reality is designed to defeat.
*   **[Security Concepts — Active Probing](../glossary/security_concepts.md)** — Why Reality's "steal from real server" approach defeats active probers.
*   **[Firewalls & Honeypots](../security/firewall_honeypot.md)** — How GFW and Iran's DPI detect non-Reality VLESS.
*   **[Protocols & Parsing](../../project/03-protocols.md)** — ConfigStream's VLESS parsing logic, validation rules, credential recovery.
