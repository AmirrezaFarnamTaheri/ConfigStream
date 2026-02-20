# Hysteria2

Hysteria2 is a feature-packed proxy protocol built on QUIC. It is designed for unreliable networks and uses Brutal congestion control to guarantee bandwidth.

## Key Features
- **UDP/QUIC**: High performance on lossy networks.
- **Brutal**: Aggressive congestion control.
- **Salamander**: Advanced obfuscation mechanism.
- **Port Hopping**: Resists port blocking.

## URI Format
```
hysteria2://auth@host:port?insecure=1&sni=example.com&obfs=salamander&obfs-password=pass#Remarks
```

## Intelligence Score
- **Speed**: 10/10 (High Bandwidth)
- **Stealth**: 7/10 (UDP usually throttled/blocked)
- **Reliability**: 8/10

## Sing-box Configuration
```json
{
  "type": "hysteria2",
  "tag": "proxy",
  "server": "1.1.1.1",
  "server_port": 443,
  "password": "auth",
  "tls": {
    "enabled": true,
    "server_name": "example.com",
    "insecure": true
  },
  "obfs": {
    "type": "salamander",
    "password": "pass"
  }
}
```
