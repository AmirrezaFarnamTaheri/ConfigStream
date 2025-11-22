# API Reference

ConfigStream generates static JSON/YAML artifacts. These are your "endpoints".

**Base URL:** `https://YOUR_USERNAME.github.io/ConfigStream/output/`

## 1. Subscription Files

| File | Format | Description |
| :--- | :--- | :--- |
| `singbox.json` | JSON | **Sniper Mode**. Best for routers. Contains Routing Rules (blocked sites -> proxy, local -> direct). |
| `singbox-vpn.json` | JSON | **Tank Mode**. Best for apps. Routes ALL traffic through the proxy (TUN mode). |
| `clash.yaml` | YAML | Standard Clash configuration. |
| `base64.txt` | Text | Standard Base64 subscription string. Compatible with v2rayNG, Streisand, etc. |
| `shadowrocket.txt` | Text | Optimized for Shadowrocket (iOS). |
| `sip008.json` | JSON | SIP008 standard format for Shadowsocks. |

## 2. Metadata & Statistics

### `metadata.json`
Contains system health data.

```json
{
  "last_updated_utc": "2023-10-27T10:00:00Z",
  "total_fetched": 15000,
  "total_tested": 8000,
  "total_working": 2500,
  "version": "4.0.0",
  "protocol_colors": {
    "vmess": "#ff0000",
    "vless": "#00ff00"
  }
}
```

### `summary.json`
Contains granular stats for the analytics dashboard.

```json
{
  "protocols": {
    "vmess": 1200,
    "vless": 800,
    "trojan": 500
  },
  "countries": {
    "US": 500,
    "DE": 300,
    "SG": 200
  }
}
```
