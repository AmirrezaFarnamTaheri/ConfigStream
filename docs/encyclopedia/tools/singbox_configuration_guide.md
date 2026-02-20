# Sing-box Configuration Guide

ConfigStream relies heavily on [Sing-box](https://sing-box.sagernet.org/) as its core engine for testing and output generation.

## Structure

### Inbounds
How traffic enters the proxy client.
- **TUN**: Creates a virtual network interface (VPN mode).
- **Mixed**: SOCKS5 + HTTP proxy on a single port.

### Outbounds
Where traffic goes.
- **Proxy**: The actual server (VMess, VLESS, etc.).
- **Direct**: Traffic that bypasses the proxy (local LAN, domestic IPs).
- **Block**: Traffic to block (Ads, tracking).
- **DNS**: DNS queries.

### Route
Rules that decide which Outbound to use.
- **GeoIP**: Route based on IP country.
- **Geosite**: Route based on domain category (e.g. `geosite:google` -> Proxy).

## Example Outbound (VLESS)
```json
{
  "type": "vless",
  "tag": "MyProxy",
  "server": "1.1.1.1",
  "server_port": 443,
  "uuid": "...",
  "tls": {
    "enabled": true,
    "server_name": "example.com",
    "utls": {
      "enabled": true,
      "fingerprint": "chrome"
    }
  }
}
```
