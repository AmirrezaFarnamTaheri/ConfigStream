# Hysteria2 Protocol

## Overview
Hysteria2 (Hy2) is a high-performance proxy protocol built on [QUIC](../glossary/networking_terms.md) (HTTP/3). It is designed for speed in lossy network environments — where packet loss is high and traditional TCP-based protocols struggle. Hysteria2 uses aggressive congestion control (Brutal) that intentionally "bullies" through packet loss, maintaining high throughput even on degraded connections.

> **Analogy**: TCP-based protocols are like polite drivers who slow down when they see traffic. Hysteria2 is a fire truck with sirens on — it barrels through congestion at full speed, pushing other traffic aside. This is great when you need to get somewhere fast, but it's not fair to other drivers on the road.

Hysteria2 is particularly effective in regions where ISPs throttle international traffic, as its UDP-based transport and custom congestion control can push through bandwidth restrictions that cripple TCP protocols like [VLESS](vless.md), [Trojan](trojan.md), and [VMess](vmess.md).

## How It Works

1.  **QUIC Connection**: The client establishes a QUIC (UDP) connection to the server on the configured port.
2.  **Authentication**: The client sends a password in the initial QUIC handshake. The server validates it.
3.  **Tunneling**: Once authenticated, the client can request TCP or UDP connections to arbitrary destinations. The server proxies them.
4.  **Congestion Control**: Hysteria2 uses the "Brutal" algorithm — instead of backing off when packet loss is detected (like TCP does), it maintains a target bandwidth regardless of loss. This is why it feels fast on throttled networks.

### Why QUIC?
*   **Encrypted Headers**: QUIC encrypts everything, including transport headers. Censors can see it's UDP but cannot inspect the contents.
*   **Multiplexing**: Multiple streams share one connection without head-of-line blocking (unlike HTTP/2 over TCP).
*   **0-RTT Resumption**: Returning connections can send data immediately without a handshake round-trip.

### The Bandwidth Trade-Off
Brutal congestion control is aggressive by design. It will consume the bandwidth you configure (`up`/`down` parameters) regardless of network conditions. This means:
*   On a 100 Mbps connection with 5% loss, Hysteria2 will still push ~95 Mbps.
*   On a shared network, it may starve other users' connections.
*   ISPs may detect and throttle the unusual UDP traffic pattern.

> **Real-world example**: An Iranian user on a 50 Mbps ADSL line with 10% international packet loss sees ~5 Mbps with [VLESS](vless.md) (TCP backs off aggressively). With Hysteria2 configured for 50 Mbps, they see ~45 Mbps — Brutal compensates for the loss by sending redundant packets. The trade-off: their roommate's video call stutters because Hysteria2 is consuming most of the bandwidth.

### Salamander Obfuscation

By default, Hysteria2's QUIC traffic is identifiable — censors can see the QUIC header format. Salamander adds a layer of obfuscation that scrambles the QUIC packets, making them look like random UDP noise instead of QUIC.

```
Without Salamander: Client → [QUIC packets, identifiable] → Server
With Salamander:    Client → [Random-looking UDP, unidentifiable] → Server
```

Salamander requires a shared password between client and server. It adds ~1-2% overhead but significantly improves stealth against QUIC-aware DPI.

## URI Format

```
hysteria2://PASSWORD@HOST:PORT?sni=DOMAIN&insecure=0&obfs=salamander&obfs-password=OBFS_PASS#REMARK
```

Alternate scheme: `hy2://`

### Key Parameters

| Parameter | Purpose | Notes |
| :--- | :--- | :--- |
| `PASSWORD` | Authentication password | In userinfo portion of URI |
| `sni` | TLS Server Name Indication | For certificate verification |
| `insecure` | Skip TLS verification | `0` (verify) or `1` (skip). ConfigStream preserves but flags. |
| `obfs` | Obfuscation type | `salamander` — adds a layer of obfuscation over QUIC |
| `obfs-password` | Obfuscation password | Required if `obfs` is set |
| `ports` | Port hopping range | e.g., `1000-2000`. Client rotates ports to evade blocking. |

### Port Hopping
Hysteria2 supports port hopping — the client periodically switches to a different port within a configured range. This makes it harder for censors to block by port number. ConfigStream parses port hopping syntax but may simplify complex rules for client compatibility.

## ConfigStream Parsing

1.  Extract password from the userinfo portion.
2.  Parse query parameters: `sni`, `insecure`, `obfs`, `obfs-password`, `ports`.
3.  **Obfuscation**: If `obfs=salamander`, include obfuscation config in output.
4.  **Port Hopping**: Parse `ports=START-END` syntax. Store in details for clients that support it.
5.  **Validation**: Password must not be empty. Host must be valid.

## Sing-box Configuration

### Standard Hysteria2
```json
{
  "type": "hysteria2",
  "tag": "proxy-hy2",
  "server": "server.example.com",
  "server_port": 443,
  "password": "your-password",
  "tls": {
    "enabled": true,
    "server_name": "server.example.com"
  }
}
```

### With Salamander Obfuscation
```json
{
  "type": "hysteria2",
  "tag": "proxy-hy2-obfs",
  "server": "server.example.com",
  "server_port": 443,
  "password": "your-password",
  "obfs": {
    "type": "salamander",
    "password": "obfs-password"
  },
  "tls": {
    "enabled": true,
    "server_name": "server.example.com"
  }
}
```

## Hysteria2 vs TUIC

Both are QUIC-based, but they differ in philosophy:

| Aspect | Hysteria2 | TUIC |
| :--- | :--- | :--- |
| **Congestion Control** | Brutal (aggressive) | BBR / Cubic (standard) |
| **Speed on Lossy Networks** | Excellent | Good |
| **Network Fairness** | Poor (intentionally aggressive) | Fair |
| **Obfuscation** | Salamander | None built-in |
| **Port Hopping** | Yes | No |
| **UDP Relay** | Full | Full (with QUIC streams) |

## Vulnerability: UDP Blocking

The biggest weakness of Hysteria2 (and all QUIC-based protocols) is blanket UDP blocking. During [internet shutdowns in Iran](../security/firewall_honeypot.md), all non-DNS UDP traffic is dropped, making Hysteria2 completely unusable.

> **When does this happen?** Iran blocks UDP during protests, elections, and political unrest. China's GFW throttles (but usually doesn't fully block) UDP. Russia has experimented with QUIC blocking. During these events, only TCP-based protocols ([VLESS](vless.md), [Trojan](trojan.md), [VMess](vmess.md), [Shadowsocks](shadowsocks.md)) or [WARP shielding](../networking/warp.md) survive.

ConfigStream handles this gracefully — Hysteria2 proxies that fail testing during UDP shutdowns are automatically candidates for [revival via WARP chains](../../project/04-engineering.md), which wrap them in a TCP-based tunnel.

## Protocol Intelligence Scores

| Metric | Score | Notes |
| :--- | :--- | :--- |
| **Stealth** | 6/10 | QUIC is identifiable. Salamander helps but is not TLS-level camouflage. |
| **Speed** | 10/10 | Brutal congestion control maximizes throughput. |
| **Reliability** | 7/10 | Excellent when UDP is open. Useless when UDP is blocked. |
| **Penalty (km)** | 0 | No routing penalty — preferred for speed-optimized chains. |

## Client Compatibility

| Client | Support | Notes |
| :--- | :--- | :--- |
| Sing-box | Full | Native support, including obfs and port hopping |
| Clash Meta | Full | Native support |
| V2RayN | Full | Via sing-box core |
| Shadowrocket | Full | iOS |
| Surge | Partial | Basic support |
| Clash Premium | No | Does not support Hysteria2 |

## Related Documentation

*   **[WireGuard Protocol](wireguard.md)** — Another high-speed protocol; kernel-level but even less stealthy.
*   **[VLESS Protocol](vless.md)** — TCP-based stealth alternative when UDP is blocked.
*   **[Shadowsocks Protocol](shadowsocks.md)** — Lightweight TCP alternative with wide client support.
*   **[Sing-box Configuration Guide](../tools/singbox_configuration_guide.md)** — How Hysteria2 outbounds are structured in Sing-box JSON.
*   **[Networking Terms — QUIC, MTU](../glossary/networking_terms.md)** — The transport protocol Hysteria2 is built on, and why MTU matters for UDP tunnels.
*   **[Firewalls & Honeypots — Iran](../security/firewall_honeypot.md)** — Why Hysteria2 fails during Iran's UDP shutdowns.
*   **[Protocols & Parsing](../../project/03-protocols.md)** — ConfigStream's Hysteria2 parsing logic, port hopping syntax.
