# 03. Protocol Deep Dive

This document explains how ConfigStream handles the parsing, validation, and testing of modern censorship-resistant proxy protocols.

## Supported Protocols

| Protocol | Parsing Logic | Validation | Test Client |
| :--- | :--- | :--- | :--- |
| **VLESS** | `src/configstream/parsers.py:_parse_vless` | Check UUID, Address, Port. If `security=reality`, check `pbk`. | Sing-box |
| **VMess** | `src/configstream/parsers.py:_parse_vmess` | Decode Base64 -> JSON. Validate `id`, `add`, `port`, `aid`. | Sing-box |
| **Trojan** | `src/configstream/parsers.py:_parse_trojan` | `trojan://password@host:port`. Ensure password exists. | Sing-box |
| **Shadowsocks** | `src/configstream/parsers.py:_parse_ss` | Decode Base64 (SIP002). Validate cipher & password. | Sing-box |
| **Hysteria 2** | `src/configstream/parsers.py:_parse_hysteria2` | `hy2://password@host:port`. Check obfuscation keys. | Sing-box |
| **WireGuard** | `src/configstream/parsers.py:_parse_wireguard` | Check `private_key`, `peer_public_key`. Parse `reserved` bytes for WARP. | Sing-box |
| **OpenVPN** | `src/configstream/parsers.py:_parse_openvpn` | Regex scan for `remote host port` and `BEGIN CERTIFICATE`. | N/A (Parsing only) |

## VLESS & REALITY: The New Standard

**VLESS** is a stateless lightweight transport protocol. **REALITY** replaces traditional TLS by forwarding traffic to a legitimate foreign website (the SNI) during the handshake, making the proxy server look exactly like that website (e.g., `microsoft.com` or `yahoo.com`) to censors.

### Critical Fields
-   **UUID**: User ID.
-   **Flow**: `xtls-rprx-vision` (optional, for XTLS Vision).
-   **Reality Fields**:
    -   `pbk`: Public Key (Curve25519). **Mandatory**.
    -   `sid`: Short ID. **Mandatory**.
    -   `fp`: Fingerprint (e.g., `chrome`, `firefox`).
    -   `sni`: The domain being mimicked.

### Parsing Logic
Our parser enforces strict checking for REALITY configs to avoid generating broken links.

```python
# src/configstream/parsers.py
if details.get("security") == "reality":
    if not details.get("pbk"):
        logger.debug("VLESS Reality missing 'pbk'")
        return None
```

## VMess: Legacy but Popular

VMess relies on a complex handshake and is stateful (VMessAEAD). It is often distributed as a Base64-encoded JSON blob (`vmess://ey...`).

### The "Type" Confusion
VMess links do not follow a standard URI scheme. They are just `vmess://` followed by base64.
We decode this blob and map the often-inconsistent JSON keys (e.g., `add` vs `host` vs `ip`) to a normalized `Proxy` object.

## WireGuard & Cloudflare WARP

WireGuard is a Layer 3 protocol. It is not designed for censorship circumvention but is fast. Cloudflare WARP uses a modified WireGuard protocol.

### Reserved Bytes
To distinguish WARP traffic, the client sends 3 reserved bytes in the handshake.
-   **Parsing**: We extract `reserved` from the URL query parameters (often CSV or base64 encoded).
-   **Output**: When generating Sing-box config, we pass `reserved` as an array of integers.

## Obfuscation & Security

### TLS Fingerprint Randomization (uTLS)
To avoid identification by the "Client Hello" packet size/structure, modern clients use **uTLS**.
ConfigStream simulates this during testing by randomizing HTTP headers (order and casing) when fetching sources, and the underlying `sing-box` tester uses uTLS "chrome" or "randomized" fingerprints when probing proxies.

### Deep Packet Inspection (DPI) Evasion
We prioritize protocols that support:
-   **Padding**: Adding random noise to packet sizes.
-   **Mux**: Multiplexing streams (though this can degrade performance on poor networks).
-   **Fragment**: Splitting "Client Hello" packets.
