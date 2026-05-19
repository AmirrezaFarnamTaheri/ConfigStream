# VMess Protocol

## Overview
VMess (V2Ray Mess) is the original proxy protocol from the V2Ray project. It provides built-in encryption and authentication, making it a self-contained tunneling solution. VMess was the dominant circumvention protocol for years and remains widely deployed, though newer protocols like [VLESS](vless.md) and [Trojan](trojan.md) are increasingly preferred for their simplicity and stealth.

> **Analogy**: If proxy protocols were cars, VMess is a heavily armored SUV — it carries its own bulletproof glass (encryption) even when driving through a tunnel that's already bulletproof (TLS). It's safe, but the extra weight slows it down. [VLESS](vless.md) is the same SUV without the redundant armor — faster, lighter, and just as safe inside the tunnel.

## How It Works

1.  **Authentication**: Each connection begins with a header encrypted using the user's UUID. The header contains a timestamp (must be within 90 seconds of server time), a random encryption key, and the target address.
2.  **Encryption**: The payload is encrypted using [AES-128-GCM or ChaCha20-Poly1305](../glossary/security_concepts.md) (selected by the `security` field, usually `auto`). This is the "double encryption" — VMess encrypts the data, then [TLS](../glossary/networking_terms.md) encrypts it again.
3.  **AlterID**: Originally, VMess used AlterID > 0 to generate multiple valid authentication headers for replay protection. Non-zero AlterID is **insecure** — it is vulnerable to replay attacks. ConfigStream forces AlterID to 0 ([AEAD mode](../glossary/security_concepts.md)) for all VMess proxies.

### Time Sensitivity
VMess requires the client and server clocks to be synchronized within **90 seconds**. If your device time is wrong, all VMess connections will fail silently. This is the #1 cause of "connected but no internet" issues with VMess.

> **Why 90 seconds?** The timestamp in the VMess header is used to prevent replay attacks. The server rejects any header with a timestamp more than 90 seconds from its own clock. On mobile devices, this is a common problem — phones that have been offline for a while may have drifted clocks. **Fix**: Enable automatic time sync in your device settings.

### The Double Encryption Problem

When VMess runs over TLS (which is almost always), your data is encrypted twice:

```
Your data → VMess encryption (AES-128-GCM) → TLS encryption (AES-256-GCM) → Network
```

This wastes CPU cycles and adds ~2-5ms of latency per packet. On low-power devices (phones, routers), this overhead is noticeable. VLESS eliminates the inner layer entirely, trusting TLS to handle confidentiality — which it does perfectly well.

## URI Format

VMess URIs are Base64-encoded JSON objects:
```
vmess://BASE64_JSON
```

### Decoded JSON Structure
```json
{
  "v": "2",
  "ps": "Remark Name",
  "add": "server.example.com",
  "port": "443",
  "id": "uuid-here",
  "aid": "0",
  "scy": "auto",
  "net": "ws",
  "type": "none",
  "host": "cdn-domain.com",
  "path": "/vmess-ws",
  "tls": "tls",
  "sni": "cdn-domain.com"
}
```

### Critical Fields

| Field | Purpose | Notes |
| :--- | :--- | :--- |
| `id` | UUID for authentication | **Mandatory**. Must be a valid UUID. |
| `aid` | AlterID | **Must be 0**. Non-zero is insecure. ConfigStream forces this. |
| `net` | Transport type | `tcp`, `ws`, `grpc`, `h2` |
| `scy` | Encryption method | Usually `auto`. Options: `aes-128-gcm`, `chacha20-poly1305`, `none`. |
| `tls` | TLS enabled | `tls` or empty string |
| `sni` | TLS Server Name | Used for certificate verification |
| `type` | TCP header obfuscation | `none` or `http` (HTTP header masquerading) |

## Transport Options

| Transport | Fields | Use Case |
| :--- | :--- | :--- |
| **TCP** | `net=tcp`, `type=none/http` | Direct connection. `http` type adds HTTP header obfuscation. |
| **WebSocket** | `net=ws`, `path`, `host` | CDN-compatible. Most common transport for VMess. |
| **gRPC** | `net=grpc`, `path` (serviceName) | Multiplexed, CDN-compatible. |
| **HTTP/2** | `net=h2`, `path`, `host` | Multiplexed over TLS. |

## ConfigStream Parsing

1.  Decode Base64 (with automatic padding correction).
2.  Parse JSON. Handle both string and integer types for `port` and `aid`.
3.  **Force AlterID to 0** regardless of source value.
4.  Normalize transport: `net` field maps to transport type.
5.  Extract TLS settings from `tls`, `sni` fields.
6.  **Credential Recovery**: If `id` is empty, check alternative JSON keys before dropping.
7.  **Validation**: UUID must be present and valid. Drop if missing.

## Sing-box Configuration

### VMess + WebSocket + TLS
```json
{
  "type": "vmess",
  "tag": "proxy-vmess",
  "server": "server.example.com",
  "server_port": 443,
  "uuid": "your-uuid-here",
  "security": "auto",
  "alter_id": 0,
  "tls": {
    "enabled": true,
    "server_name": "server.example.com",
    "utls": { "enabled": true, "fingerprint": "chrome" }
  },
  "transport": {
    "type": "ws",
    "path": "/vmess-ws",
    "headers": { "Host": "server.example.com" }
  }
}
```

## VMess vs VLESS

| Aspect | VMess | VLESS |
| :--- | :--- | :--- |
| **Encryption** | Built-in (AES-GCM / ChaCha20) | None (relies on TLS) |
| **CPU Usage** | Higher (double encryption with TLS) | Lower |
| **Time Sensitivity** | Yes (90-second clock sync) | No |
| **Reality Support** | No | Yes |
| **Maturity** | Older, battle-tested | Newer, actively developed |
| **Stealth** | Good with WS+TLS | Excellent with Reality |

## Protocol Intelligence Scores

| Metric | Score | Notes |
| :--- | :--- | :--- |
| **Stealth** | 8/10 | Good with WS+TLS, but no Reality support. |
| **Speed** | 6/10 | Double encryption adds overhead. |
| **Reliability** | 8/10 | Mature, well-tested. |
| **Penalty (km)** | 200 | Moderate routing penalty in chain scoring. |

## Client Compatibility

| Client | Support | Notes |
| :--- | :--- | :--- |
| Sing-box | Full | TCP, WS, gRPC, H2 |
| Clash Meta | Full | TCP, WS, gRPC, H2 |
| V2RayN/NG | Full | All transports (native protocol) |
| Shadowrocket | Full | All transports |
| Surge | Full | TCP, WS |
| Loon | Full | TCP, WS |
| Quantumult X | Full | TCP, WS |

## Related Documentation

*   **[VLESS Protocol](vless.md)** — VMess's lightweight successor; no double encryption, supports Reality.
*   **[Shadowsocks Protocol](shadowsocks.md)** — Simpler alternative; no UUID, symmetric key only.
*   **[Sing-box Configuration Guide](../tools/singbox_configuration_guide.md)** — How VMess outbounds are structured in Sing-box JSON.
*   **[Networking Terms — TLS, WebSocket](../glossary/networking_terms.md)** — Transport concepts used by VMess.
*   **[Security Concepts — UUID, AEAD](../glossary/security_concepts.md)** — Why UUID is mandatory and how AEAD encryption works.
*   **[Protocols & Parsing](../../project/03-protocols.md)** — ConfigStream's VMess parsing logic, Base64 JSON decoding, AlterID enforcement.
