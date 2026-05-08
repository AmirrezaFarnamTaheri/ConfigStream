# Shadowsocks Protocol

## Overview
Shadowsocks (SS) is one of the earliest and most widely deployed censorship circumvention protocols. Created in 2012 by a Chinese developer (`clowwindy`), it was designed to look like random noise to [DPI](../glossary/networking_terms.md) systems. Shadowsocks encrypts traffic using symmetric ciphers and proxies it through a remote server. Its simplicity and speed made it the backbone of anti-censorship efforts for over a decade.

> **Analogy**: If [VLESS](vless.md) is a spy wearing a perfect disguise (Reality), Shadowsocks is a spy wearing an invisibility cloak — you can't see what they look like, but you *can* see that something invisible is walking around. Advanced censors have learned to detect the "invisible" footprint.

**SS2022** is the modern evolution, introducing BLAKE3 key derivation and built-in replay protection — fixing the cryptographic weaknesses that plagued earlier versions.

## How It Works

1.  **Connection**: The client connects to the server (typically on a high port like 8388 or 443).
2.  **Encryption**: The first bytes contain an encrypted header with the target address. The entire stream is encrypted using a symmetric [AEAD cipher](../glossary/security_concepts.md) (e.g., AES-256-GCM, ChaCha20-Poly1305).
3.  **Proxying**: The server decrypts the header, connects to the target, and relays traffic bidirectionally.

Unlike [Trojan](trojan.md) or [VLESS](vless.md), Shadowsocks does **not** use TLS. The encryption is applied directly to the TCP stream — there is no TLS handshake, no certificate exchange, no SNI field. This makes it simpler but also means there's no "cover story" for the traffic.

### The Randomness Problem
Shadowsocks traffic looks like random bytes — no recognizable headers, no TLS handshake, no HTTP structure. While this defeats simple pattern matching, advanced DPI (particularly China's [GFW](../security/firewall_honeypot.md)) can detect Shadowsocks by its *lack* of structure.

> **Why?** Normal internet traffic is never perfectly random. HTTPS has structured TLS records. HTTP has headers. DNS has fixed formats. A stream of pure random bytes is itself a fingerprint — like a person in a crowd wearing no clothes at all. They're not wearing a uniform, but they still stand out.

This is why Shadowsocks scores 7/10 for stealth — it defeats basic DPI but fails against ML-based [entropy analysis](../glossary/security_concepts.md).

## Cipher Methods

### Modern AEAD Ciphers (Recommended)
| Cipher | Key Size | Notes |
| :--- | :--- | :--- |
| `aes-256-gcm` | 32 bytes | Fast on hardware with AES-NI. Most common. |
| `aes-128-gcm` | 16 bytes | Slightly faster, slightly less secure. |
| `chacha20-ietf-poly1305` | 32 bytes | Fast on mobile/ARM without AES-NI. |

### SS2022 Ciphers
| Cipher | Key Format | Notes |
| :--- | :--- | :--- |
| `2022-blake3-aes-128-gcm` | Base64 (16 bytes) | SS2022 with AES. |
| `2022-blake3-aes-256-gcm` | Base64 (32 bytes) | SS2022 with AES-256. |
| `2022-blake3-chacha20-poly1305` | Base64 (32 bytes) | SS2022 with ChaCha20. |

### Insecure Stream Ciphers (Dropped by ConfigStream)
`aes-256-cfb`, `rc4-md5`, `chacha20` — These lack authentication and are vulnerable to replay and injection attacks. An attacker can flip bits in the ciphertext and the receiver won't detect the tampering. ConfigStream drops proxies using these ciphers during parsing.

> **Example**: A proxy source provides `ss://YWVzLTI1Ni1jZmI6cGFzc3dvcmQ=@1.2.3.4:8388`. ConfigStream decodes this to `aes-256-cfb:password`, sees the insecure cipher, and drops it with a `DEBUG` log: `Dropped SS proxy: insecure method aes-256-cfb`.

## URI Formats

### SIP002 (Preferred)
```
ss://BASE64(method:password)@host:port#remark
```

### Classic Format
```
ss://BASE64(method:password@host:port)#remark
```

### SS2022 Format
```
ss://2022-blake3-aes-256-gcm:BASE64_KEY@host:port#remark
```

### SIP003 Plugins
```
ss://BASE64(method:password)@host:port?plugin=v2ray-plugin%3Bserver%3Btls%3Bhost%3Dexample.com#remark
```

## ConfigStream Parsing

1.  Detect format variant (SIP002, Classic, or Plain).
2.  Decode Base64 with automatic padding correction.
3.  Extract `method` and `password`. For SS2022, the password is a Base64-encoded key.
4.  **Method Validation**: Reject invalid method names (`ss`, `shadowsocks`, empty). Only accept known AEAD or SS2022 ciphers.
5.  **Plugin Handling**: Parse SIP003 plugin parameters (`v2ray-plugin`, `obfs-local`). Normalize arguments for cross-client compatibility.
6.  **Credential Recovery**: If method or password is empty after primary parsing, attempt alternative field extraction before dropping.

## Sing-box Configuration

### Standard Shadowsocks
```json
{
  "type": "shadowsocks",
  "tag": "proxy-ss",
  "server": "server.example.com",
  "server_port": 8388,
  "method": "aes-256-gcm",
  "password": "your-password"
}
```

### SS2022
```json
{
  "type": "shadowsocks",
  "tag": "proxy-ss2022",
  "server": "server.example.com",
  "server_port": 8388,
  "method": "2022-blake3-aes-256-gcm",
  "password": "BASE64_KEY_HERE"
}
```

## Shadowsocks vs SS2022

| Aspect | Shadowsocks (AEAD) | SS2022 |
| :--- | :--- | :--- |
| **Key Derivation** | EVP_BytesToKey (weak, MD5-based) | BLAKE3 (modern, fast, collision-resistant) |
| **Replay Protection** | Bloom filter (optional, server-side) | Built-in nonce counter (mandatory) |
| **Detection Resistance** | Moderate (random bytes fingerprint) | Improved (header padding, length hiding) |
| **Key Format** | Password string (any text) | Base64-encoded fixed-length key |
| **Compatibility** | Universal (all clients) | Sing-box, Clash Meta only |

> **When to use which?** If your clients support SS2022, always prefer it — the cryptography is strictly better. If you need maximum client compatibility (Surge, Quantumult X, older V2RayN), use standard AEAD with `aes-256-gcm` or `chacha20-ietf-poly1305`.

## Protocol Intelligence Scores

| Metric | Score | Notes |
| :--- | :--- | :--- |
| **Stealth** | 7/10 | Random-looking but detectable by ML-based DPI. |
| **Speed** | 8/10 | Lightweight encryption, low overhead. |
| **Reliability** | 9/10 | Battle-tested, extremely stable. |
| **Penalty (km)** | 200 | Moderate routing penalty in chain scoring. |

## Client Compatibility

| Client | SS (AEAD) | SS2022 | Notes |
| :--- | :--- | :--- | :--- |
| Sing-box | Full | Full | Native support |
| Clash Meta | Full | Full | Native support |
| V2RayN/NG | Full | Partial | Depends on core version |
| Shadowrocket | Full | Full | iOS |
| Surge | Full | No | macOS/iOS |
| Quantumult X | Full | No | iOS |

## Related Documentation

*   **[VLESS Protocol](vless.md)** — Higher stealth (Reality), but requires UUID and more complex setup.
*   **[Hysteria2 Protocol](hysteria2.md)** — QUIC-based alternative; faster but UDP-dependent.
*   **[Sing-box Configuration Guide](../tools/singbox_configuration_guide.md)** — How Shadowsocks outbounds are structured in Sing-box JSON.
*   **[Networking Terms — TLS, ALPN](../glossary/networking_terms.md)** — Transport-layer concepts relevant to SS plugin transports.
*   **[Security Concepts — AEAD, Replay Protection](../glossary/security_concepts.md)** — Why AEAD ciphers replaced stream ciphers, and how SS2022 adds replay protection.
*   **[Protocols & Parsing](../../project/03-protocols.md)** — ConfigStream's SS parsing logic, SIP002/SIP003 handling, cipher validation.
