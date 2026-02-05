# Censorship Evasion Features

This document describes the advanced anti-censorship features implemented in ConfigStream.

## Overview

ConfigStream implements multiple layers of censorship evasion to help users bypass network restrictions, DNS poisoning, and DPI (Deep Packet Inspection) blocking.

## Features

### 1. DNS Hardening

#### DNS-Safe Outputs (IP-Only)
- **Purpose**: Bypass DNS poisoning by using pre-resolved IP addresses
- **Implementation**: All hostnames are resolved to IPs before inclusion
- **SNI Preservation**: Original hostnames are preserved in TLS SNI and Host headers
- **Outputs**: All formats have `-dns-safe` variants (e.g., `base64-dns-safe.txt`)

#### DNS-Hardened Outputs (Prefer IP)
- **Purpose**: Use encrypted DNS (DoH/DoT/DoQ) while preferring IPs when available
- **Implementation**: 
  - Multiple DoH/DoT/DoQ resolvers with fallback ordering
  - Proxies use resolved IPs but keep hostnames as fallback
  - SNI/Host headers pinned to original hostname
- **Outputs**: Available for Sing-box, Clash, Shadowrocket, Surge, Loon, QuantumultX

#### FakeIP Strategy (Sing-box)
- **Purpose**: Eliminate DNS queries entirely
- **Implementation**: Client assigns fake IPs (198.18.0.0/15) locally and sends domain names through tunnel
- **Benefit**: ISP never sees DNS queries, making DNS poisoning impossible

### 2. Shielding (Copper to Gold Transformation)

#### Topology Inversion
- **Standard Washing**: `Client → Proxy → WARP → Internet`
  - Hides Proxy IP from destination (unblocks Netflix/Google)
  - **Flaw**: If Proxy IP is blocked, client cannot connect

- **Shielding**: `Client → WARP (Clean IP) → Proxy → Internet`
  - Hides Proxy IP from censor (ISP)
  - Client connects to clean Cloudflare IP first
  - Proxy traffic travels inside WARP tunnel, invisible to DPI

#### Implementation
- Method: `ProxyWasher.shield_batch()`
- Input: Failed proxies (dead copper)
- Output: Shielded chains (gold) with `GOLD-` prefix tags
- Pipeline: Automatically captures failed proxies and attempts resurrection

### 3. TLS Fingerprint Rotation

#### uTLS Fingerprinting
- **Purpose**: Make TLS handshakes look like browser traffic
- **Supported Fingerprints**: Chrome, Firefox, Safari, iOS, Android, Edge
- **Rotation**: Deterministic rotation based on proxy ID
- **Protocols**: VMess, VLESS, Trojan, Hysteria2, TUIC

#### ALPN Rotation
- **Purpose**: Vary Application-Layer Protocol Negotiation
- **Combinations**: `h2,http/1.1`, `http/1.1`, `h2`
- **Rotation**: Deterministic rotation based on proxy ID
- **Protocols**: VMess, VLESS, Trojan

### 4. Traffic Obfuscation

#### TLS Fragmentation
- **Purpose**: Break TLS handshakes into fragments to evade DPI
- **Implementation**: Configurable fragment size (default: 100-200 bytes)
- **Sleep**: Random delay between fragments (default: 0-10ms)
- **Output**: Enabled in Sniper profile by default

#### Multiplexing with Padding
- **Purpose**: Hide packet size patterns
- **Implementation**: 
  - HTTP/2 multiplexing (h2mux)
  - Random padding added to packets
  - Multiple streams per connection
- **Protocols**: VMess, VLESS, Trojan, Shadowsocks

### 5. Worker Masquerading

#### Fake Website Mode
- **Purpose**: Make Cloudflare Worker look like harmless website
- **Implementation**: 
  - Root path serves content from legitimate site (e.g., kernel.org)
  - Proxy tunnel only accessible via secret path (`/my-secret-tunnel`)
  - Active probes see normal website, not proxy
- **File**: `tools/worker.js`

### 6. HTML Smuggling

#### Config Distribution
- **Purpose**: Hide configs in HTML to evade text scanners
- **Implementation**: 
  - Config embedded in `<meta name="csrf-token">` tag
  - Base64 encoded
  - JavaScript decoder for user extraction
- **File**: `src/configstream/tools/html_smuggler.py`

### 7. Censorship Lab

#### Testing Framework
- **Purpose**: Simulate censorship scenarios for testing
- **Modes**:
  - DNS Poisoning: Returns fake IPs or NXDOMAIN
  - IP Blocking: Blocks specific IPs or ASNs
  - UDP Blocking: Drops UDP packets
  - Slow DNS: Adds latency to DNS queries
  - Timeout Simulation: Multiplies timeouts
  - Rate Limiting: Limits request rate
- **File**: `src/configstream/tools/censorship_lab.py`

### 8. Domestic Bypass Routing

#### Local Traffic Direct
- **Purpose**: Route local/domestic traffic directly (bypass VPN)
- **Implementation**: 
  - `.ir` domains → DIRECT
  - Iran IPs → DIRECT
  - Private IPs → DIRECT
- **Benefit**: Prevents breaking local services (banks, government sites)

## Usage

### DNS Profiles

Select DNS profile in frontend:
- **Standard**: Default DNS configuration
- **DNS-Safe**: IP-only endpoints (use when DNS is blocked)
- **DNS-Hardened**: Encrypted DNS with IP preference (use when DNS is poisoned)

### Gold Connections

1. Download **Nekobox** or **Sing-box** client
2. Copy subscription link: `singbox-chains.json`
3. Import as **Subscription** (not Profile)
4. Select proxies with `GOLD-` prefix

### TLS Fingerprint Rotation

Enabled by default for compatible protocols. To disable:
- Set `enable_utls=False` in evasion config
- Or remove `utls` field from outbound configs

### Censorship Lab

```python
from configstream.tools.censorship_lab import CensorshipLab, CensorshipMode

lab = CensorshipLab()
lab.configure_mode(
    CensorshipMode.DNS_POISON,
    poison_ips=["127.0.0.1"],
    nxdomain_domains=["telegram.org"],
)
```

## Output Files

### Standard Outputs
- `singbox.json` - Standard Sing-box config
- `clash.yaml` - Standard Clash config
- `base64.txt` - Standard subscription

### DNS-Safe Outputs
- `singbox-dns-safe.json` - IP-only Sing-box config
- `clash-dns-safe.yaml` - IP-only Clash config
- `base64-dns-safe.txt` - IP-only subscription

### DNS-Hardened Outputs
- `singbox-dns-hardened.json` - DoH/DoT/DoQ + prefer IP
- `clash-dns-hardened.yaml` - DoH/DoT/DoQ + prefer IP
- `shadowrocket-dns-hardened.txt` - DoH/DoT/DoQ resolvers
- `surge-dns-hardened.conf` - DoH/DoT/DoQ resolvers
- `loon-dns-hardened.conf` - DoH/DoT/DoQ resolvers
- `quantumult-dns-hardened.conf` - DoH/DoT/DoQ resolvers

### Gold/Shielded Outputs
- `singbox-chains.json` - Contains shielded chains (GOLD- prefixed)

## Technical Details

### Resolver Diversity

Primary resolvers (in order):
1. DoH: Cloudflare, Google, Quad9, AdGuard, OpenDNS, Mullvad
2. DoT: Cloudflare, Google, Quad9, AdGuard
3. DoQ: AdGuard, Google, Cloudflare

Fallback resolvers:
- Quad9 DoH
- Cloudflare DoH
- Google DoH
- Quad9 DoT
- Cloudflare DoT

### SNI/Host Pinning

When using resolved IP:
- `tls.server_name` = original hostname
- `transport.headers.Host` = original hostname (WebSocket)
- `transport.host` = [original hostname] (HTTP/2)

### Shielding Process

1. Identify failed proxies (`is_working=False`)
2. Generate WARP config with clean endpoint
3. Create proxy outbound with `detour` pointing to WARP tag
4. Tag WARP as `SHIELD-*` (not user-facing)
5. Tag proxy as `GOLD-*` (user-facing)
6. Add both to output config

## Analytics & Monitoring

ConfigStream tracks evasion metrics over time and provides visualizations:

### Time-Series Charts
- **Evasion Trend Tracking**: Metrics tracked over 7-day rolling window
  - Shielded (Gold) proxies count
  - Revived (WARP/VWARP) proxies count
  - uTLS enabled proxies count
  - DNS-Hardened proxies count
- **Data Export**: Available in `data/evasion_trend.json`
- **Visualization**: Interactive charts on statistics and analytics pages
- **Real-Time Stats**: Current metrics displayed in frontend

### Metrics Available
- Total shielded proxies (Gold connections)
- Total revived proxies (WARP/VWARP)
- Evasion feature usage (uTLS, fragmentation, multiplexing)
- DNS hardening adoption (DNS-safe, DNS-hardened)
- Success rates and trends over time

See the analytics page for detailed visualizations and trend analysis.

## Limitations

1. **Gold connections require modern clients**: Nekobox or Sing-box only
2. **Geosite rules require database**: Domestic bypass needs `geosite.db`
3. **TLS fingerprint rotation**: May break some servers (opt-in recommended)
4. **Worker masquerading**: Requires Cloudflare Worker deployment
5. **HTML smuggling**: Manual extraction required

## Best Practices

1. **Start with DNS-Safe**: If DNS is blocked, use DNS-safe outputs
2. **Upgrade to DNS-Hardened**: If DNS is poisoned, use DNS-hardened outputs
3. **Use Gold for severe restrictions**: When direct connections fail, use Gold connections
4. **Test in Censorship Lab**: Validate evasion techniques before deployment
5. **Monitor stats**: Track `shielded_count` in pipeline stats

## References

- [Sing-box Documentation](https://sing-box.sagernet.org/)
- [Clash Documentation](https://clash.gitbook.io/)
- [DoH/DoT/DoQ Standards](https://www.rfc-editor.org/rfc/rfc8484)

