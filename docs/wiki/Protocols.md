# Protocol Support

ConfigStream supports a wide range of protocols, normalizing them into a unified `Proxy` model and exporting them to standard formats like Sing-box and Clash.

## Supported Protocols

| Protocol | Support Level | Parsing | Testing | Washing |
| :--- | :--- | :--- | :--- | :--- |
| **VLESS** | Full | ✅ | ✅ | ✅ |
| **VMess** | Full | ✅ | ✅ | ✅ |
| **Trojan** | Full | ✅ | ✅ | ✅ |
| **Shadowsocks** | Full | ✅ | ✅ | ✅ |
| **Hysteria 2** | Full | ✅ | ✅ | ❌ |
| **TUIC** | Full | ✅ | ✅ | ❌ |
| **WireGuard** | Full | ✅ | ✅ | N/A |
| **SSH** | Basic | ✅ | ⚠️ | ❌ |
| **HTTP/S** | Basic | ✅ | ✅ | ❌ |
| **SOCKS5** | Basic | ✅ | ✅ | ❌ |

## Conversion Logic

### VLESS & VMess
*   **UUID**: Mandatory. Missing UUIDs result in dropped proxies.
*   **Transport**: WebSocket (`ws`), gRPC (`grpc`), HTTP/2 (`h2`), TCP (`tcp`).
*   **Security**: `tls`, `reality`, `utls`.
    *   *Note*: Reality requires a valid `pbk` (public key) and `fp` (fingerprint).

### Shadowsocks
*   **Encryption**: Validated against known ciphers (e.g., `chacha20-ietf-poly1305`, `aes-256-gcm`).
*   **Plugins**: `obfs-local`, `v2ray-plugin` are mapped to Sing-box equivalents where possible.

### WireGuard
*   **Keys**: `private_key` and `peer_public_key` are strictly validated.
*   **Endpoint**: `ip:port` must be reachable.
*   **Reserved**: Reserved bytes are handled for WARP compatibility.

## Security Policies
*   **Insecure TLS**: By default, `insecure: true` (skip verification) is enabled for free proxies to maximize compatibility, as many use self-signed certs.
*   **Port Restrictions**: Ports 22, 23, 25, 445 are blocked by the `SecurityValidator`.
*   **Localhost**: Proxies pointing to private ranges (127.0.0.1, 192.168.x.x) are dropped.
