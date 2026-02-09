# WireGuard Protocol

## Overview
WireGuard is a modern, high-performance VPN protocol that uses state-of-the-art cryptography. It is extremely lightweight — the entire codebase is ~4,000 lines of code (compared to OpenVPN's ~100,000). WireGuard operates at the kernel level on Linux and uses UDP for transport.

> **Analogy**: If OpenVPN is a Swiss Army knife with 50 blades (features, options, legacy compatibility), WireGuard is a scalpel — one blade, perfectly sharp, does exactly one thing extremely well. The simplicity makes it faster, more auditable, and harder to misconfigure.

In ConfigStream, WireGuard is primarily used for **[Cloudflare WARP](../networking/warp.md)** tunnels (washing, shielding, and revival), but standalone WireGuard proxies from sources are also parsed and tested.

## How It Works

1.  **Key Exchange**: WireGuard uses Curve25519 for key exchange. Each peer has a static keypair. The handshake is a single round-trip (1-RTT).
2.  **Encryption**: Data is encrypted using ChaCha20-Poly1305 with a per-session symmetric key derived from the Noise protocol framework.
3.  **UDP Transport**: All traffic is encapsulated in UDP packets. There is no TCP fallback.
4.  **Stateless Design**: WireGuard has no "connection" state. Peers simply send encrypted UDP packets. If a packet is valid (correct key, correct counter), it is accepted. This makes WireGuard extremely resilient to network changes (roaming between WiFi and cellular).

### The Handshake Fingerprint Problem
WireGuard's handshake is a very distinctive 148-byte UDP packet with a fixed structure: `[type=1][sender_index=4bytes][unencrypted_ephemeral=32bytes][encrypted_static+timestamp]`. Censors (particularly China's [GFW](../security/firewall_honeypot.md)) can identify and block WireGuard by this fingerprint alone.

> **Why is this a problem?** Unlike [TLS](../glossary/networking_terms.md) (which millions of websites use), WireGuard's handshake is unique to WireGuard. Blocking it doesn't break anything else on the internet. This makes it a low-cost, high-reward target for censors.

This is why raw WireGuard connections are often blocked in heavily censored regions, and why ConfigStream wraps WireGuard (WARP) inside other tunnels or uses clean Cloudflare IPs that are too costly to block. Blocking Cloudflare's IP ranges would break half the internet.

### MTU Considerations

WireGuard adds ~60 bytes of overhead per packet (WireGuard header + UDP + IP). The default [MTU](../glossary/networking_terms.md) of 1420 works for most networks, but when WireGuard is nested inside another tunnel (as in ConfigStream's chain topology), the MTU must be reduced:

| Scenario | Recommended MTU | Why |
|---|---|---|
| Standalone WireGuard | 1420 | Standard overhead |
| WARP (Cloudflare) | 1280 | Conservative for global compatibility |
| WireGuard inside another tunnel | 1200-1280 | Double encapsulation overhead |

If MTU is too high, packets get fragmented or dropped silently — causing mysterious "connected but slow" or "some sites work, others don't" symptoms.

## URI Format

```
wireguard://PRIVATE_KEY@HOST:PORT?publickey=PEER_PUBLIC_KEY&address=LOCAL_IP&mtu=MTU&reserved=0,0,0#REMARK
```

### Key Parameters

| Parameter | Purpose | Notes |
| :--- | :--- | :--- |
| `PRIVATE_KEY` | Client private key (Base64) | In userinfo portion |
| `publickey` | Peer (server) public key | Base64-encoded Curve25519 key |
| `address` | Local tunnel address | e.g., `172.16.0.2/32` (IPv4) or `fd01::2/128` (IPv6) |
| `mtu` | Maximum Transmission Unit | Typically 1280 for WARP, 1420 for standard |
| `reserved` | Client identifier bytes | 3 comma-separated integers. Used by WARP+ for routing. |

## ConfigStream Parsing

1.  Extract private key from userinfo.
2.  Parse query parameters: `publickey`, `address`, `mtu`, `reserved`.
3.  **Address Handling**: Support both IPv4 and IPv6 local addresses. Dual-stack configs include both.
4.  **Reserved Field**: Parse `reserved=X,Y,Z` into a 3-element integer array. Default `[0,0,0]` for free-tier WARP.
5.  **Validation**: Private key and public key must be valid Base64-encoded 32-byte Curve25519 keys.

## Sing-box Configuration

```json
{
  "type": "wireguard",
  "tag": "warp-out",
  "server": "162.159.192.1",
  "server_port": 2408,
  "local_address": [
    "172.16.0.2/32",
    "fd01:db8:85a3::2/128"
  ],
  "private_key": "client-private-key-base64",
  "peer_public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
  "reserved": [0, 0, 0],
  "mtu": 1280
}
```

## Role in ConfigStream

WireGuard is not typically used as a standalone proxy protocol in ConfigStream. Its primary roles are:

1.  **WARP Tunnels**: Cloudflare WARP uses WireGuard under the hood. All [washing, shielding, and revival](../../project/04-engineering.md) operations generate WireGuard outbounds pointing to Cloudflare endpoints.
2.  **Chain Building**: WireGuard outbounds serve as the "clean exit" layer in chain topologies:
    ```
    Washing:   Client → Proxy → WireGuard/WARP → Internet  (hide proxy IP from destination)
    Shielding: Client → WireGuard/WARP → Proxy → Internet  (hide proxy IP from censor)
    ```
3.  **Standalone Parsing**: WireGuard URIs from sources are parsed and included in output for clients that support native WireGuard.

> **Note**: Clash Meta (Mihomo) supports WireGuard natively with `dialer-proxy` for chaining. Xray-core also supports WireGuard via `secretKey` + `peers[]` format. Gold/Shielded chains are available in Sing-box (`singbox-chains.json`), Clash (`clash.yaml`), and Xray JSON formats.

See [WARP & Clean IPs](../networking/warp.md) for detailed WARP-specific documentation.

## Protocol Intelligence Scores

| Metric | Score | Notes |
| :--- | :--- | :--- |
| **Stealth** | 4/10 | Distinctive 148-byte handshake. Easily fingerprinted. |
| **Speed** | 10/10 | Kernel-level, minimal overhead, excellent throughput. |
| **Reliability** | 10/10 | Stateless design handles roaming and packet loss gracefully. |
| **Penalty (km)** | 300 | High routing penalty in chain scoring (low stealth). |

## Client Compatibility

| Client | Support | Notes |
| :--- | :--- | :--- |
| Sing-box | Full | Native outbound support (deprecated in 1.11, `endpoints` in 1.13+) |
| Clash Meta / Mihomo | Full | Native support with `dialer-proxy` for chaining, AmneziaWG support |
| WireGuard App | Full | Native (official app for all platforms) |
| V2RayN | Full | Uses sing-box or Xray core, both support WireGuard |
| Xray | Full | Native outbound: `secretKey` + `peers[].publicKey` format |
| Nekobox | Full | Uses sing-box core internally |

## Related Documentation

*   **[Hysteria2 Protocol](hysteria2.md)** — Another high-speed UDP protocol; better stealth via Salamander obfuscation.
*   **[VLESS Protocol](vless.md)** — TCP-based stealth alternative when WireGuard's handshake is fingerprinted.
*   **[WARP & Clean IPs](../networking/warp.md)** — How ConfigStream uses WireGuard as the transport layer for Cloudflare WARP tunnels.
*   **[Sing-box Configuration Guide](../tools/singbox_configuration_guide.md)** — How WireGuard outbounds are structured in Sing-box JSON.
*   **[Networking Terms — MTU](../glossary/networking_terms.md)** — Why MTU tuning matters for WireGuard tunnels.
*   **[Firewalls & Honeypots](../security/firewall_honeypot.md)** — Why WireGuard's 148-byte handshake is easily fingerprinted by GFW and Iran DPI.
*   **[Protocols & Parsing](../../project/03-protocols.md)** — ConfigStream's WireGuard parsing logic.
