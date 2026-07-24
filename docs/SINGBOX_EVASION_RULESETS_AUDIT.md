# Sing-box Rule Set & Censorship Evasion Audit

This document outlines the findings from an architectural and security audit of the ConfigStream Sing-box outbound configuration pipeline.

## 1. Sing-box Outbound & Evasion Engine Flowchart

```text
       [ Incoming Proxy Models ]
                  │
                  ▼
┌────────────────────────────────────────┐
│  Protocol Converter (singbox.py)       │
│  - Strict Cipher Whitelisting          │
│  - Strip unsupported XTLS flows        │
│  - Drop invalid ports/local IPs        │
└─────────────────┬──────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────┐
│ Transport Injector (singbox_utils.py)  │
│ - WS, gRPC, HTTPUpgrade assignment     │
│ - Sanitize URI paths (% encoding)      │
│ - Reality PBK Validation & Base uTLS   │
└─────────────────┬──────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────┐
│ Evasion Enrichment (evasion.py)        │
│ - uTLS & ALPN Daily Hash Rotation      │
│ - TCP Fragmentation & Mux Injection    │
│ - TFO / MPTCP enablement               │
└─────────────────┬──────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────┐
│ Config Assembly (generators/singbox.py)│
│ - Apply DNS Profiles (Safe vs Hardened)│
│ - Inject Geosite/GeoIP Routing         │
│ - Construct final sing-box JSON        │
└────────────────────────────────────────┘
```

## 2. uTLS, ALPN, & Fragmentation Evasion Compliance Matrix

| Feature | Supported Parameters | Evasion Logic / Constraints |
|---------|----------------------|-----------------------------|
| **uTLS Fingerprint** | `chrome`, `firefox`, `safari`, `ios`, `android`, `edge`, `randomized` | Reality connections default to `chrome`. Evasion engine rotates across safe profiles (Chrome, Firefox, Safari, iOS) using a time-seeded hash (`_rotation_hash`). |
| **ALPN Settings** | `h2`, `http/1.1`, `http/1.0` | Validates against schema. Rotates securely across HTTP/2 and HTTP/1.1 combinations to avoid deep packet inspection fingerprinting. |
| **TCP Fragmentation** | `light`, `medium`, `heavy`, `all`, `none` | Pre-configured `tlshello` chunking intervals. Automatically applied to VMess/VLESS/Trojan, but explicitly **disabled** for `reality` and `xtls-rprx-vision` flows to prevent protocol breakage. |
| **Multiplexing** | `h2mux`, `smux`, `yamux` | Automatically appends `h2mux` with padding enabled. Note: Currently disabled by default during tests due to CI/kernel requirements. |

## 3. DNS Safe vs Hardened Routing Rule Audit Table

The generation logic (`dns_profiles.py` and `generators/singbox.py`) categorizes DNS lookups to prevent DNS leakage while allowing fast local resolution.

| DNS Profile | Transport / Protocol | Detour Route | Rule Sets Addressed | Security Posture |
|-------------|----------------------|--------------|---------------------|------------------|
| **Remote (Hardened)** | `1.1.1.1` (UDP) / `DoH` | `🌍 Proxy Select` (Proxied) | `clash_mode: Global`, Default Final | **Strong**: Encrypts queries via outbound proxy. `dns_profiles.py` upgrades to `https://cloudflare-dns.com/dns-query`. |
| **Direct (Safe)** | `8.8.8.8` / `dns.google` | `direct` | `geosite-private`, `geosite-ir`, `clash_mode: Direct` | **Moderate**: Safely resolves local and IR domains without routing them through the VPN tunnel. |
| **Block (Blackhole)**| `rcode://success` | N/A | `geosite-category-ads-all` | **Strict**: Terminates ad/tracker domains directly at the client DNS resolver layer. |
| **Local (Loopback)** | `1.1.1.1` | `direct` | `sing_box-ProxyChain` | **Internal**: Dedicated listener loopback. |

## 4. Schema Validation & Transport Encoding Findings

- **Cipher Enforcement**: `valid_ss_methods` restricts Shadowsocks ciphers strictly to Sing-box compatible AEAD suites (e.g., `aes-128-gcm`, `chacha20-ietf-poly1305`, `2022-blake3-*`). Legacy CFB ciphers correctly fall through to rejection.
- **XTLS Flow Pruning**: Directly strips legacy and incompatible flows (`xtls-rprx-direct`, `xtls-rprx-splice-udp443`) per `singbox_outbound.schema.json` constraints, ensuring the engine does not panic.
- **VLESS UDP Stability**: Injects `packet_encoding: xudp` automatically for VLESS payloads, mitigating silent UDP packet drops.
- **Path Sanitization**: Employs `_BAD_PERCENT_RE` to detect and fix malformed percent-encoding in WebSocket paths, preventing Sing-box deserialization crashes.
- **Host Array Formatting**: Correctly isolates `host_key` (SSH) and `host` (HTTP) attributes as strict arrays/lists matching schema boundaries.

## 5. Hardening & Security Recommendations

1. **DNS DoH Standardization**: `generators/singbox.py` currently hardcodes the remote DNS address as `1.1.1.1` (UDP) whereas `dns_profiles.py` uses the stronger `https://cloudflare-dns.com/dns-query` (DoH). Standardize on DoH for the base generator to mitigate MITM interception of proxy DNS resolution.
2. **Periodic Rotation Connection Dropping**: The `_rotation_hash` rotates uTLS and ALPN signatures daily. Ensure the Sing-box core is instructed to drain rather than sever active TCP connections upon config re-loads to prevent daily drops.
3. **Fragmentation on Vision**: Currently, `evasion.py` excludes `xtls-rprx-vision` from fragmentation. Given advanced GFW heuristics, research whether Vision handshakes can tolerate lightweight fragmentation natively.
4. **Local Hostname Validation**: `_LOCAL_HOSTNAMES` and `ip_is_private` logic drops private IPs. Ensure malicious DNS records mapping public domains to local IPs (DNS Rebinding) are mitigated at the routing layer.
