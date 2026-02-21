# Official Documentation Reference

**Purpose:** Central reference for external docs used by ConfigStream. Use for schema validation, format compliance, and troubleshooting. All URLs verified against live documentation (2026-02).

---

## Schema Compliance Summary (Verified 2026-02)

| Component | Schema Source | ConfigStream Status |
|------------|---------------|---------------------|
| Sing-box Shadowsocks | [outbound/shadowsocks](https://sing-box.sagernet.org/configuration/outbound/shadowsocks/) | ✅ `VALID_SS_METHODS` whitelist; `method`, `password`, `server`, `server_port` |
| Sing-box WireGuard | [outbound/wireguard](https://sing-box.sagernet.org/configuration/outbound/wireguard/) | ✅ `private_key`, `peer_public_key`, `mtu` (1280); deprecated 1.11, removed 1.13 |
| Sing-box VMess | [outbound/vmess](https://sing-box.sagernet.org/zh/configuration/outbound/vmess/) | ✅ `uuid`, `alter_id`, `security` (cipher) |
| Sing-box VLESS | [outbound/vless](https://sing-box.sagernet.org/zh/configuration/outbound/vless/) | ✅ `uuid`, `flow` (xtls-rprx-vision only) |
| Surge proxy chain | [policy/proxy](https://manual.nssurge.com/policy/proxy.html) | ✅ `underlying-proxy` for WireGuard-over-Proxy |
| Loon node chain | [Node](https://nsloon.app/docs/Node/) | ✅ `proxy=` for WireGuard chains |
| Mihomo relay | [relay](https://wiki.metacubex.one/en/config/proxy-groups/relay/) | ⚠️ **WireGuard does NOT support relay**; use `dialer-proxy` or sing-box |
| Clash chains | — | ❌ **Not implemented**; `clash.yaml` has standard proxies only; chains only in sing-box |

---

## Vwarp (voidr3aper-anon/Vwarp)

| Resource | URL | Notes |
|----------|-----|-------|
| **Repo** | https://github.com/voidr3aper-anon/Vwarp | |
| **Config struct** | https://github.com/voidr3aper-anon/Vwarp/blob/master/config/config.go | `UnifiedConfig`, `WireGuardConfig`, `MASQUEConfig` |
| **Root command** | https://github.com/voidr3aper-anon/Vwarp/blob/master/cmd/vwarp/rootcmd.go | CLI flags, `--masque`, `--masque-preferred`, `--noize-preset` |
| **Noize presets** | https://github.com/voidr3aper-anon/Vwarp/blob/master/config/noize/presets.go | Built-in: minimal, light, medium, heavy, stealth, gfw, firewall |
| **Config guide** | https://raw.githubusercontent.com/voidr3aper-anon/Vwarp/master/docs/CONFIG_FORGE.md | Full reference; JunkInterval, masque.enabled, masque.preferred |
| **Sample config** | https://raw.githubusercontent.com/voidr3aper-anon/Vwarp/master/docs/examples/sample-working.json | Working example with JunkInterval |
| **SOCKS guide** | https://github.com/voidr3aper-anon/Vwarp/blob/master/docs/SOCKS_PROXY_GUIDE.md | |
| **Releases** | https://github.com/voidr3aper-anon/Vwarp/releases | v2.2.2 latest |

### Version Compatibility

| ConfigStream | Vwarp binary | Config format |
|--------------|--------------|---------------|
| vwarp.py | **v2.2.2** (default) | Full JSON support (JunkInterval, masque.enabled, masque.preferred) |
| — | **v2.1.x** | Set `VWARP_VERSION=v2.1.0`; sanitization strips unsupported fields |

**ConfigStream defaults to v2.2.2** (latest verified in this doc audit). Override with `VWARP_VERSION` env for older binaries.

### Official sample-working.json (master, verified)

- `wireguard.atomicnoize.JunkInterval`: 15000000 (nanoseconds)
- `masque.enabled`, `masque.preferred`: supported in master
- CLI: `vwarp --config sample-working.json --masque`

---

## Sing-box

| Resource | URL | Notes |
|----------|-----|-------|
| **Outbound** | https://sing-box.sagernet.org/configuration/outbound/ | |
| **WireGuard** | https://sing-box.sagernet.org/configuration/outbound/wireguard/ | `mtu`, `peers`, `private_key`, `peer_public_key`; deprecated 1.11, removed 1.13 |
| **Shadowsocks** | https://sing-box.sagernet.org/configuration/outbound/shadowsocks/ | Methods, password |
| **VLESS** | https://sing-box.sagernet.org/zh/configuration/outbound/vless/ | `uuid`, `flow` |
| **VMess** | https://sing-box.sagernet.org/zh/configuration/outbound/vmess/ | `uuid`, `alter_id`, cipher |
| **Migration** | https://sing-box.sagernet.org/migration/#migrate-wireguard-outbound-to-endpoint | WireGuard outbound → endpoint |

**ConfigStream:** Uses WireGuard outbound with `"mtu": 1280` per AGENTS.md. Migration to endpoint recommended for sing-box 1.13+.

---

## IPFS

| Resource | URL | Notes |
|----------|-----|-------|
| **Gateway** | https://docs.ipfs.tech/concepts/ipfs-gateway/ | Path: `https://{gateway}/ipfs/{CID}/{optional path}` |
| **Web addressing** | https://docs.ipfs.tech/how-to/address-ipfs-on-web/ | Subdomain, path, DNSLink |
| **Path semantics** | — | Canonical: `/ipfs/{CID}/{optional path to resource}` |

---

## Pinata

| Resource | URL | Notes |
|----------|-----|-------|
| **Upload (v3)** | https://docs.pinata.cloud/files/uploading-files | `POST https://uploads.pinata.cloud/v3/files`, multipart/form-data |
| **Pinning** | https://docs.pinata.cloud/pinning/listing-files | |
| **Legacy API** | `https://api.pinata.cloud/pinning/pinFileToIPFS` | Used by `scripts/publish_ipfs.py`; still supported |

---

## Python

| Resource | URL | Notes |
|----------|-----|-------|
| **urllib.parse.parse_qs** | https://docs.python.org/3/library/urllib.parse.html#urllib.parse.parse_qs | `&`-separated query params |

---

## Client Formats

| Resource | URL | Notes |
|----------|-----|-------|
| **Surge** | https://manual.nssurge.com/policy/proxy.html | Proxy policy; `underlying-proxy` for chains |
| **Loon** | https://nsloon.app/docs/Node/ | Node format; `proxy=` for WireGuard chains |
| **Mihomo relay** | https://wiki.metacubex.one/en/config/proxy-groups/relay/ | **WireGuard does NOT support relay**; use dialer-proxy |
| **Mihomo VMess** | https://wiki.metacubex.one/en/config/proxies/vmess/ | `uuid`, `alterId`, `cipher` |
| **Mihomo Trojan** | https://wiki.metacubex.one/en/config/proxies/trojan/ | `password`, `sni` |
| **Mihomo WG** | https://wiki.metacubex.one/config/proxies/wg/ | `private-key`, `public-key`, `mtu`, `dialer-proxy` |
| **Sing-box migration** | https://sing-box.sagernet.org/migration/#migrate-wireguard-outbound-to-endpoint | WireGuard outbound → endpoint (1.13+) |
