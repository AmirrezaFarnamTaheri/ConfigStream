# API Reference

ConfigStream produces static JSON/YAML artifacts. These are served via GitHub Pages and act as a read-only API.

## Core Endpoints

### `proxies.json`
The master list of all working proxies.
```json
[
  {
    "protocol": "vmess",
    "address": "1.2.3.4",
    "port": 443,
    "uuid": "...",
    "country_code": "US",
    "latency": 120,
    "is_working": true,
    "details": {
      "net": "ws",
      "tls": "tls",
      "sni": "example.com"
    }
  }
]
```

### `metadata.json`
Statistics and system status for the frontend.
```json
{
  "last_updated_utc": "2023-10-27T10:00:00+00:00",
  "total_proxies": 1542,
  "total_working": 850,
  "countries": { "US": 400, "DE": 200 },
  "protocols": { "vmess": 500, "vless": 350 },
  "latency_distribution": {
    "fast": 100,
    "medium": 400,
    "slow": 300,
    "very_slow": 50
  }
}
```

### `vectors.json`
**New in v1.4**: Feature vectors for client-side similarity search.
```json
{
  "proxy_uuid_hash": [3, 8, 1, 4, 2, 0, 0, 0],
  ...
}
```
*   **Vector Schema**: `[ProtocolHash, CountryHash, LatencyBucket, PortHash, ISPHash, SecScore, StabScore, RelScore]`
*   Used by the frontend to find "proxies like this one" without a backend vector DB.

## Subscription Endpoints

*   `/output/singbox.json`: Sing-box "Sniper" config (Routing-focused).
*   `/output/singbox-vpn.json`: Sing-box "Tank" config (Tun/VPN-focused).
*   `/output/clash.yaml`: Clash.Meta configuration.
*   `/output/base64.txt`: Standard base64 subscription list.
