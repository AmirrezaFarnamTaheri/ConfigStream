# Trojan Protocol

Trojan mimics standard HTTPS traffic to bypass censorship. It encapsulates traffic in TLS and looks like a normal web server to passive observers.

## Key Features
- **HTTPS Mimicry**: Designed to be indistinguishable from a web server.
- **Fallback**: If a non-Trojan packet is received (e.g. active probe), it redirects to a real web server.
- **Simplicity**: Single password authentication.

## URI Format
```
trojan://password@host:port?security=tls&sni=example.com#Remarks
```

## Intelligence Score
- **Speed**: 9/10
- **Stealth**: 8/10
- **Reliability**: 8/10

## Sing-box Configuration
```json
{
  "type": "trojan",
  "tag": "proxy",
  "server": "1.1.1.1",
  "server_port": 443,
  "password": "password",
  "tls": {
    "enabled": true,
    "server_name": "example.com"
  }
}
```
