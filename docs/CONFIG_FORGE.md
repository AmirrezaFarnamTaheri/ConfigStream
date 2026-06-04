# vwarp Configuration & Chaining Reference

This unified reference covers connection options, obfuscation settings (MASQUE/AtomicNoize), and proxy chaining for the `vwarp` tool.

## 📄 Core Configuration
`vwarp` uses a single, unified JSON-based configuration file that combines all settings.

### Basic Settings
```json
{
  "version": "1.0",
  "bind": "127.0.0.1:8086",            // SOCKS5 listen address
  "endpoint": "162.159.192.1:2408",    // WARP endpoint
  "key": "your-license-key",           // Optional WARP+ key
  "dns": "1.1.1.1",
  "proxy": "socks5://127.0.0.1:1080"   // Upstream chain (Double-VPN)
}
```

## 🛡️ Obfuscation Technologies

ConfigStream leverages two main obfuscation technologies in `vwarp` to bypass Deep Packet Inspection (DPI):

### 1. MASQUE Noize
Obfuscates QUIC traffic at the MASQUE tunnel level.
*   **Techniques**: Signature packet injection, protocol mimicry (HTTPS/DNS/STUN), and dynamic padding.
*   **Presets**:
    | Preset | Overhead | Best For |
    |---|---|---|
    | `light` | Minimal | Corporate firewalls |
    | `moderate` | Medium | ISP-level filtering |
    | `gfw` | High | Severe state censorship |

### 2. AtomicNoize
Makes WireGuard traffic appear as legitimate IPsec/IKEv2 traffic.
*   **Junk Packets**: Hides the WireGuard handshake fingerprint using decoy UDP packets.
*   **Junk Count (`Jc`)**: Configurable from 10 (`light`) to 85 (`heavy`).

## 🔗 SOCKS5 Proxy Chaining (Double/Triple VPN)

Route WARP traffic through an existing proxy for maximum privacy or to change exit locations.

### Common Use Cases
*   **Bypass Advanced Censorship**: Chain WARP through a local VPN to hide WireGuard patterns.
*   **Change Exit Location**: Use WARP for speed while routing through a specific geographic location.
*   **Triple-VPN**: Combine Psiphon, WARP, and an external proxy.

### CLI Examples
```bash
# Double VPN: App -> vwarp -> SOCKS5 -> Internet
vwarp --proxy socks5://user:pass@host:port --masque

# Triple VPN with Psiphon
vwarp --cfon --country US --proxy socks5://127.0.0.1:1080 --bind 127.0.0.1:8086
```

## ⚙️ Configuration Comparison

| Feature | Sample-Working ⭐ | Basic | Moderate | Heavy |
|---------|------------------|-------|----------|--------|
| **MASQUE Junk Packets** | 15 | 5-10 | 15-25 | 30-50 |
| **AtomicNoize Junk (Jc)** | 25 | 10-20 | 25-50 | 50-100 |
| **Protocol Mimicry** | HTTPS | QUIC | HTTPS | HTTPS |
| **Global Compatibility** | ✅ Excellent | ⚠️ Limited | ✅ Good | ✅ Maximum |

See `docs/CENSORSHIP_EVASION.md` for high-level evasion strategies and selection guidance.
