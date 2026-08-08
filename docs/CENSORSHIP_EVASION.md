# Censorship Evasion

ConfigStream implements eight layers of censorship evasion — from DNS hardening to steganographic delivery — designed to defeat [Deep Packet Inspection (DPI)](wiki/encyclopedia/glossary/networking_terms.md), DNS poisoning, IP blocking, and traffic analysis. This is the single unified reference for all anti-censorship features, configuration, and troubleshooting.

> **Analogy**: Think of censorship as a series of checkpoints on a highway. DNS poisoning is a fake road sign pointing you the wrong way. DPI is a guard inspecting every car's contents. IP blocking is a roadblock at a specific intersection. ConfigStream gives you fake license plates (uTLS), tinted windows (multiplexing), alternate routes (shielding), and invisible tunnels (WARP chains) to get through all of them.

---

## Evasion Modes

ConfigStream provides three evasion modes, controlled by the `EVASION_MODE` environment variable. Each mode progressively adds more techniques:

| Mode | uTLS | Multiplexing | ALPN | Overhead | Use Case |
|---|---|---|---|---|---|
| `standard` | — | — | — | 0ms | No censorship, maximum compatibility |
| `stealth` | Yes | — | — | ~5ms | Moderate DPI (Turkey, Egypt, Pakistan) |
| `aggressive` (default) | Yes | Yes | Yes | ~10-20ms | Heavy DPI (Iran, China, Russia) |

```bash
# Set via environment variable
export EVASION_MODE=aggressive

# Or in .env file
EVASION_MODE=stealth
```

### Choosing the Right Mode

| Your Situation | Recommended Mode | DNS Profile | Output File |
|---|---|---|---|
| Normal network, occasional blocks | `standard` | Standard | `singbox.json` |
| DNS poisoning, basic DPI | `stealth` | DNS-Safe | `singbox-dns-safe.json` |
| Severe blocking, DNS poisoning, DPI | `aggressive` | DNS-Hardened | `singbox-dns-hardened.json` |
| Extreme censorship, ISP-level blocking | `aggressive` | DNS-Hardened | `singbox-chains.json` (Gold/Shielded) |

**Escalation strategy**: Start with `standard`. If connections fail, escalate to `stealth`, then `aggressive`. If even aggressive mode fails, use Gold/Shielded chains from `singbox-chains.json`.

---

## 1. DNS Hardening

DNS is the first thing censors attack — it's the phone book of the internet. If the censor controls DNS, they can redirect you to fake servers or simply say "that domain doesn't exist."

### DNS-Safe Outputs (IP-Only)

Bypasses DNS poisoning entirely by pre-resolving all hostnames to IP addresses before including them in configs. Your device never makes a DNS query for the proxy server.

- **How it works**: The pipeline resolves `proxy.example.com` → `203.0.113.42` and writes the IP directly into the config.
- **SNI Preservation**: The original hostname is preserved in [TLS SNI](wiki/encyclopedia/glossary/networking_terms.md) and Host headers so the proxy server still knows which virtual host you're connecting to.
- **Outputs**: Every format has a `-dns-safe` variant (e.g., `base64-dns-safe.txt`, `clash-dns-safe.yaml`).

### DNS-Hardened Outputs (Encrypted DNS)

Uses encrypted DNS protocols ([DoH, DoT, DoQ](wiki/encyclopedia/glossary/networking_terms.md)) while preferring pre-resolved IPs when available. This is the belt-and-suspenders approach.

**Resolver diversity** (in priority order):

| Protocol | Resolvers |
|---|---|
| **DoH** (DNS over HTTPS) | Cloudflare, Google, Quad9, AdGuard, OpenDNS, Mullvad |
| **DoT** (DNS over TLS) | Cloudflare, Google, Quad9, AdGuard |
| **DoQ** (DNS over QUIC) | AdGuard, Google, Cloudflare |

**Fallback chain**: If the primary resolver is blocked, the client automatically tries the next one. Six resolvers across three protocols means the censor would need to block all 18 endpoints simultaneously.

### FakeIP Strategy (Sing-box)

Eliminates DNS queries entirely. The client assigns fake local IPs (from the `198.18.0.0/15` range) and sends domain names through the tunnel. Your ISP never sees a single DNS query — making DNS poisoning impossible.

### SNI/Host Pinning

When using a resolved IP, the original hostname is preserved in three places to ensure the proxy server accepts the connection:

```
tls.server_name = "proxy.example.com"           # TLS SNI field
transport.headers.Host = "proxy.example.com"     # WebSocket Host header
transport.host = ["proxy.example.com"]           # HTTP/2 authority
```

---

## 2. Shielding (Copper to Gold Transformation)

Shielding is ConfigStream's most powerful evasion technique. It inverts the proxy topology so the censor never sees the proxy's IP address.

### The Problem: Blocked Proxy IPs

Standard washing hides the proxy IP from the *destination* (unblocks Netflix/Google):
```
Client → [Proxy IP visible to ISP] → WARP → Internet
```
But if the censor blocks the proxy IP, the client can't connect at all.

### The Solution: Topology Inversion

Shielding hides the proxy IP from the *censor* by putting WARP first:
```
Client → [Clean Cloudflare IP] → WARP tunnel → Proxy → Internet
```
The ISP only sees a connection to a Cloudflare IP — indistinguishable from visiting any Cloudflare-hosted website. The proxy traffic travels *inside* the encrypted WARP tunnel, invisible to DPI.

> **Analogy**: Standard washing is like putting on a disguise *after* you've already been seen entering the building. Shielding is like entering through a secret tunnel that starts from a public library — nobody knows you went to the building at all.

### Shielding Process (Step by Step)

1. Pipeline tests all proxies. Some fail (these are "dead copper").
2. `ProxyWasher.shield_batch()` generates a WARP WireGuard config with a clean Cloudflare endpoint.
3. Creates a proxy outbound with `detour` pointing to the WARP outbound tag.
4. Tags the WARP outbound as `SHIELD-{id}` (internal, not user-facing).
5. Tags the proxy outbound as `GOLD-{id}` (user-facing, appears in selectors).
6. Both outbounds are added to the output config.
7. Typically resurrects 10-30% of dead proxies.

### Using Gold Connections

1. Download **Nekobox** or **Sing-box** client.
2. Import subscription: `singbox-chains.json`.
3. Select proxies with `GOLD-` prefix — these are shielded.

---

## 3. TLS Fingerprint Evasion

### uTLS Fingerprinting

Every TLS client has a unique "fingerprint" (called [JA3](wiki/encyclopedia/glossary/security_concepts.md)) based on the cipher suites, extensions, and curves it advertises in the ClientHello. Standard Go/Python TLS libraries have a very distinctive fingerprint that censors can block instantly.

**Solution**: uTLS replaces the default fingerprint with a real browser's fingerprint. The censor sees what looks like Chrome 120 browsing the web, not a proxy tool.

| Fingerprint | Mimics | Assignment |
|---|---|---|
| `chrome` | Chrome 120 | Default |
| `firefox` | Firefox 118 | Rotated per proxy ID |
| `safari` | Safari 17 | Rotated per proxy ID |
| `ios` | iOS Safari | Rotated per proxy ID |
| `edge` | Edge (Chromium) | Rotated per proxy ID |
| `android` | Android Chrome | Rotated per proxy ID |

**Deterministic rotation**: The same proxy always gets the same fingerprint across runs (based on a hash of the proxy ID). This prevents session churn.

**Applied to**: [VMess](wiki/encyclopedia/protocols/vmess.md), [VLESS](wiki/encyclopedia/protocols/vless.md), [Trojan](wiki/encyclopedia/protocols/trojan.md), [Hysteria2](wiki/encyclopedia/protocols/hysteria2.md), TUIC — any protocol with TLS.

### ALPN Rotation

[ALPN (Application-Layer Protocol Negotiation)](wiki/encyclopedia/glossary/networking_terms.md) tells the server which HTTP version the client supports. Some censors block connections with specific ALPN values.

ConfigStream rotates ALPN values deterministically per proxy: `h2`, `http/1.1`, or `h2,http/1.1`. This prevents ALPN-based filtering.

---

## 4. Traffic Obfuscation & Hardening

### TCP Fast Open (TFO)

Reduces connection handshake latency by sending data payload in the initial TCP SYN packet. This eliminates one round-trip time (RTT) during connection establishment and bypasses simple SYN-packet content scanners.

- **Benefit**: Faster connections and evasion of stateful handshake blockers.
- **Applied to**: VMess, VLESS, Trojan, Shadowsocks, HTTP, SOCKS5, Hysteria2, TUIC.

### Multipath TCP (MPTCP)

Enables a single TCP connection to split traffic across multiple network interfaces (e.g., Wi-Fi and mobile cellular data simultaneously).


- **Benefit**: Ensures uninterrupted connectivity if one path is blocked or degraded, and spreads packet patterns across distinct routes to confuse DPI observers.
- **Applied to**: VMess, VLESS, Trojan, Shadowsocks, HTTP, SOCKS5, Hysteria2, TUIC.

### TLS Padding

Appends random padding lengths to the TLS ClientHello handshake packet. Many DPI classifiers target the characteristic length signature of proxy handshakes.

- **Benefit**: Obfuscates the packet size footprint of the initial handshake to look like arbitrary HTTPS traffic.
- **Applied to**: VMess, VLESS, Trojan, Hysteria2, TUIC.

### Encrypted Client Hello (ECH)

Encrypts the sensitive parameters of the TLS ClientHello (most importantly the Server Name Indication, or SNI) using a public key published by the destination server.

- **Benefit**: Prevents intermediate network censors from reading the target server name during connection negotiation, rendering SNI blocklists ineffective.
- **Applied to**: VMess, VLESS, Trojan, Hysteria2, TUIC.

### Evasion Strategy Presets

To simplify client-side setup, the Laboratory interface includes high-level strategy templates:

- **Default Bypass**: Applies standard browser mimicry with uTLS Chrome fingerprint rotation.
- **Hardened Firewall**: Configures maximum obfuscation, enabling uTLS fingerprint rotation, ALPN protocol rotation, multiplexing with random padding, TCP Fast Open, Multipath TCP, and TLS padding.
- **Minimal Latency**: Prioritizes raw throughput and low latency by pairing TCP Fast Open, Multipath TCP, and Yamux multiplexing.
- **Strict SNI Obfuscation**: Focuses on bypassing SNI-level blocklists using randomized uTLS fingerprints, strict HTTP/2 ALPN, TLS padding, and ECH.

### Multiplexing with Padding

Bundles multiple streams into a single HTTP/2 connection using h2mux. Random padding bytes are added to each frame, defeating packet-size-based traffic analysis.

- **Protocol**: h2mux (HTTP/2 multiplexing)
- **Padding**: Random bytes added to each frame
- **Effect**: Traffic looks like standard HTTP/2 browsing with variable-size responses
- **Applied to**: VMess, VLESS, Trojan, Shadowsocks

---

## 5. Worker Masquerading & BYOW

### Worker Masquerading

A Cloudflare Worker that looks like a harmless website to censors:
- **Root path** (`/`) serves content from a legitimate site (e.g., `kernel.org`)
- **Secret path** (`/my-secret-tunnel`) activates the proxy tunnel
- **Active probers** see a normal website, not a proxy

### BYOW (Bring Your Own Worker) — Private Bridge

The "Hydra Strategy": instead of one shared worker that censors can block, each user deploys their own.

**Benefits**:
- **Quota Isolation**: Your own 100k/day Cloudflare quota is not shared with public users
- **Operator Control**: Your own Worker domain and deployment lifecycle
- **Availability Diversity**: Many user-operated domains are harder to exhaust than one shared endpoint, though no bridge should be described as guaranteed against blocking
- **Zero Cost**: Cloudflare's free tier is sufficient

**How to deploy**:
1. Click "Deploy to Cloudflare Workers" on the ConfigStream frontend.
2. Log in to Cloudflare (free account) and authorize.
3. Copy your Worker URL (e.g., `your-worker.username.workers.dev`).
4. Paste the URL in the frontend and click "Generate Private Bridge."
5. Download your personalized config and import it into Nekobox/Sing-box.
6. Select a `GOLD-` prefixed proxy — traffic now routes through *your* Worker.

**Files**: `tools/worker.js` (Worker code), `tools/wrangler.toml` (deployment config), `frontend/assets/js/byow.js` (frontend injection).

---

## 6. HTML Smuggling

Hides proxy configs inside HTML pages to evade text-based content scanners. The config is embedded in a `<meta name="csrf-token">` tag as Base64, with a JavaScript decoder for extraction. A network administrator inspecting the page sees a normal HTML document. Implemented via steganography (`stego.py`) and frontend assets; HTML smuggling is validated via stego tests.

---

## 7. Domestic Bypass Routing (Geosite Integration)

ConfigStream downloads [Sing-box routing databases](wiki/encyclopedia/tools/singbox_configuration_guide.md) (`geosite.db`, `geoip.db`) from SagerNet and builds intelligent route rules:

| Rule | Action | Why |
|---|---|---|
| `.ir` domains | `DIRECT` | Iranian domestic sites don't need VPN |
| Iran IP ranges | `DIRECT` | Banks, government sites must be direct |
| Private IPs (`192.168.*`, `10.*`) | `DIRECT` | Local network access |
| Google, Telegram, Twitter, YouTube, Meta | `PROXY` | Forced through proxy outbound |
| Everything else | `PROXY` | Default route |

```bash
# Download routing databases
python -m configstream.cli update-databases
```

If databases are missing, routing falls back to a simple "proxy everything" rule.

---

## 8. Censorship Lab (Testing Framework)

A simulation framework for testing evasion techniques against synthetic censorship scenarios:

| Mode | Simulates | Example |
|---|---|---|
| `DNS_POISON` | Fake DNS responses | `telegram.org` → `127.0.0.1` |
| `IP_BLOCK` | IP/ASN blocking | Block all DigitalOcean IPs |
| `UDP_BLOCK` | UDP packet dropping | Kills Hysteria2/TUIC/WARP |
| `SLOW_DNS` | DNS latency injection | 5-second DNS delays |
| `TIMEOUT` | Connection timeout multiplication | 3x all timeouts |
| `RATE_LIMIT` | Request throttling | 10 req/min |

```python
from configstream.tools.censorship_lab import CensorshipLab, CensorshipMode

lab = CensorshipLab()
lab.configure_mode(
    CensorshipMode.DNS_POISON,
    poison_ips=["127.0.0.1"],
    nxdomain_domains=["telegram.org"],
)
```

---

## 9. Vwarp Integration (MASQUE, AtomicNoize, Psiphon)

ConfigStream integrates with [vwarp](https://github.com/voidr3aper-anon/Vwarp) — an enhanced Cloudflare WARP client with advanced obfuscation — to provide additional censorship resistance beyond standard WireGuard chains.

### MASQUE Tunneling

MASQUE (Multiplexed Application Substrate over QUIC Encryption) routes WARP traffic through QUIC tunnels instead of raw WireGuard UDP. This makes WARP traffic look like standard HTTPS/QUIC browsing to DPI systems.

**Noize presets** (increasing obfuscation):

| Preset | Junk Packets | Latency Impact | Fragmentation | Best For |
|---|---|---|---|---|
| `light` | 2 | +10-20ms | No | Corporate firewalls |
| `moderate` | 3 | +30-50ms | No | ISP-level filtering |
| `heavy` | 6 | +50-100ms | Yes (512B) | State-level censorship |
| `gfw` | 15 | +50-100ms | Yes + SNI | China, Iran, Russia |

**ConfigStream usage**: The `VwarpTool.build_vwarp_config(masque_preset="gfw")` method generates a complete vwarp JSON config with the selected preset. The pipeline uses this when starting a vwarp tunnel for proxy revival.

### AtomicNoize Protocol

AtomicNoize obfuscates WireGuard traffic by injecting signature packets and junk traffic that mimics IKEv2/IPsec. This defeats DPI systems that fingerprint WireGuard's distinctive 4-packet handshake.

**Presets**: `light` (Jc=10), `moderate` (Jc=25), `heavy` (Jc=85). Higher Jc = more junk packets = harder to fingerprint but more bandwidth overhead.

### Psiphon Chaining

vwarp supports Psiphon integration (`--cfon --country <CODE>`) to change the virtual NAT exit location. Supported countries include US, CA, BR, GB, DE, FR, IT, ES, NL, JP, SG, AU, IN, and 15+ more European nations.

**Use case**: When WARP exits in a country where the destination is blocked, Psiphon reroutes through a different exit.

### SOCKS5 Proxy Chaining (Double-VPN)

vwarp can route WireGuard traffic through a SOCKS5 proxy (`--proxy socks5://host:port`), creating a double-VPN configuration:

```
Application → WARP SOCKS5 (8086) → WireGuard → SOCKS5 Proxy → Internet
```

This hides WireGuard patterns from the SOCKS5 provider and hides your real IP from Cloudflare.

### Pipeline Integration with vwarp

1. **IP Scanning**: `VwarpTool.scan_endpoints()` uses vwarp's built-in `--scan` to find unblocked Cloudflare IPs.
2. **Tunnel Management**: `VwarpTool.start_tunnel()` starts a SOCKS5 tunnel with automatic config generation (MASQUE/AtomicNoize/Psiphon support).
3. **Revival**: `ProxyWasher.wash_failed(use_vwarp=True)` wraps failed proxies in vwarp chains tagged `VWARP-REVIVE-*`.
4. **Config Generation**: `VwarpTool.build_vwarp_config()` produces configs aligned with vwarp's official CONFIG_FORGE.md format.

**Files**: `src/configstream/tools/vwarp.py` (binary controller), `src/configstream/intelligence/washer/core.py` (chain generation).

---

## Pipeline Integration

```
CI: Download geosite/geoip databases
 ↓
Fetch & Parse: Sources → Proxy objects (26+ protocols)
 ↓
Test: Go sidecar tests with evasion features applied (avoids false negatives)
 ↓
Evasion Injection: split.py enriches outbounds based on EVASION_MODE
 ↓
Route Rules: singbox.py adds geosite/geoip routing (domestic bypass)
 ↓
Wash & Shield: ProxyWasher wraps proxies in WARP chains
 ↓
Metrics: output_handler.py counts evasion feature usage → metadata.json
 ↓
Output: All 60+ files generated with evasion features embedded
```

---

## Output Files

| Category | Sing-box | Clash | Base64 | Shadowrocket | Surge | Loon | Quantumult X |
|---|---|---|---|---|---|---|---|
| **Standard** | `singbox.json` | `clash.yaml` | `base64.txt` | `shadowrocket.txt` | `surge.conf` | `loon.conf` | `quantumult.conf` |
| **DNS-Safe** | `singbox-dns-safe.json` | `clash-dns-safe.yaml` | `base64-dns-safe.txt` | `shadowrocket-dns-safe.txt` | `surge-dns-safe.conf` | `loon-dns-safe.conf` | `quantumult-dns-safe.conf` |
| **DNS-Hardened** | `singbox-dns-hardened.json` | `clash-dns-hardened.yaml` | `base64-dns-hardened.txt` | `shadowrocket-dns-hardened.txt` | `surge-dns-hardened.conf` | `loon-dns-hardened.conf` | `quantumult-dns-hardened.conf` |
| **Gold/Shielded** | `chains.json` | — | — | — | Surge chains | Loon chains | — |

Each category also generates `proxies-*.txt` (plaintext URIs), `chosen/base64-*.txt` (curated subset), `sip008-*.json`, and `side_products-*.zip`.
Gold/Shielded chains have DNS variants too: `chains-dns-safe.json` and `chains-dns-hardened.json`.

---

## Analytics & Monitoring

All evasion metrics are exported to `metadata.json` and tracked over a 7-day rolling window in `data/evasion_trend.json`:

```json
{
  "evasion_utls_enabled": 3800,
  "evasion_alpn_enabled": 3200,
  "evasion_fragmentation_enabled": 0,
  "evasion_multiplexing_enabled": 3500,
  "evasion_dns_safe_count": 4300,
  "evasion_dns_hardened_count": 4300,
  "shielded_count": 85
}
```

**Frontend visualization**: Visit the Analytics page → "Evasion Metrics Over Time" chart. Trends show:
- **Increasing**: Evasion features working effectively.
- **Stable**: Consistent performance.
- **Decreasing**: May indicate increased censorship — consider escalating evasion mode.

---

## Troubleshooting

### Connection Failures with Aggressive Mode
Some servers don't support multiplexing or ALPN rotation. Try `stealth` mode first, then `standard` if issues persist.

### False Negatives in Testing
The Go tester applies evasion features during testing to avoid false negatives. A proxy that only works *with* uTLS will be correctly identified as working.

### Gold Connections Not Working
- The Cloudflare endpoint may be blocked in your region — try a different Clean IP.
- WARP key quota may be exhausted — rotate keys via `WARP_KEY_POOL`.
- Gold connections require a modern client (Sing-box, Nekobox, Clash Meta/Mihomo, or Xray-core).

---

## Testing

```bash
# Run all evasion-related tests
pytest tests/unit/test_evasion.py tests/unit/security/test_censorship.py -v
```

Coverage includes: TLS fingerprint rotation, ALPN rotation, multiplexing with padding, outbound enrichment, and censorship connectivity checks. (TLS fragmentation disabled; use vwarp AtomicNoize for fragmentation-based evasion.) Censorship simulation (tools/censorship_lab) is available for manual testing; HTML smuggling is validated via stego tests.

---

## Limitations

1. **Gold connections require modern clients**: Sing-box, Nekobox, Clash Meta/Mihomo, or Xray-core (all support WireGuard chaining).
2. **Geosite rules require database**: Domestic bypass needs `geosite.db` — download via `update-databases`.
3. **uTLS may break some servers**: Rare, but some servers reject non-standard fingerprints.
4. **Worker masquerading requires deployment**: User must deploy their own Cloudflare Worker for BYOW.
5. **HTML smuggling requires manual extraction**: Not automated in clients.
6. **UDP blocking kills Hysteria2/TUIC/WARP**: During [Iran-style UDP shutdowns](wiki/encyclopedia/security/firewall_honeypot.md), only TCP protocols (VLESS, Trojan, VMess, SS) survive.

---

## Related Documentation

*   **[Networking Terms](wiki/encyclopedia/glossary/networking_terms.md)** — TLS, SNI, DPI, QUIC, ALPN, WebSocket, MTU explained.
*   **[Security Concepts](wiki/encyclopedia/glossary/security_concepts.md)** — AEAD, Replay Protection, Entropy Analysis, Circuit Breaker, Fail-Open.
*   **[Firewalls & Honeypots](wiki/encyclopedia/security/firewall_honeypot.md)** — GFW, Iran, Russia censorship systems and how ConfigStream defeats them.
*   **[WARP & Clean IPs](wiki/encyclopedia/networking/warp.md)** — Cloudflare WARP mechanics, scanning, shielding topology.
*   **[Sing-box Configuration Guide](wiki/encyclopedia/tools/singbox_configuration_guide.md)** — How outbound configs, routing rules, and DNS settings are structured.
*   **[Output files and client formats](wiki/project/08-api-reference.md)** — All 60+ output file variants.
*   **[Security & Privacy](wiki/project/07-security.md)** — Threat model, blocklists, log sanitization.
*   **[API Reference — Tagging System](wiki/project/08-api-reference.md)** — Evasion tags (`EVASION:UTLS`, `EVASION:FRAG`, `DNS:SAFE`, etc.).
