# WireGuard

WireGuard is a modern, high-performance VPN protocol. ConfigStream uses it primarily for **Cloudflare WARP** integration (washing and shielding).

## Key Features
- **Kernel-level**: Extremely fast.
- **Simplicity**: Minimal code base, easy configuration.
- **WARP**: Used as the transport layer for Cloudflare WARP.

## URI Format
```
wireguard://private_key@host:port?public_key=pub&reserved=1,2,3&address=172.16.0.2/32&mtu=1280#Remarks
```

## Intelligence Score
- **Speed**: 10/10
- **Stealth**: 2/10 (Easily detected DPI signature)
- **Reliability**: 9/10 (Unless blocked)

## Sing-box Configuration
```json
{
  "type": "wireguard",
  "tag": "proxy",
  "server": "1.1.1.1",
  "server_port": 2408,
  "local_address": ["172.16.0.2/32"],
  "private_key": "priv",
  "peer_public_key": "pub",
  "reserved": [1, 2, 3],
  "mtu": 1280
}
```
