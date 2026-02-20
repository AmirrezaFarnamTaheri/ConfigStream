# VMess Protocol

VMess is the original encrypted transport protocol for V2Ray. It is highly configurable but carries more overhead than VLESS due to its built-in encryption layer.

## Key Features
- **Encrypted**: Native encryption (AES-128-GCM, Chacha20-Poly1305).
- **AlterID**: Legacy mechanism for anti-replay (deprecated/removed in modern versions).
- **Transport Flexibility**: Supports WebSocket, HTTP/2, gRPC, QUIC.

## URI Format
Usually a Base64-encoded JSON object:
```json
{
  "v": "2",
  "ps": "Remarks",
  "add": "1.1.1.1",
  "port": 443,
  "id": "uuid",
  "aid": "0",
  "net": "ws",
  "type": "none",
  "host": "example.com",
  "path": "/path",
  "tls": "tls"
}
```

## Intelligence Score
- **Speed**: 7/10
- **Stealth**: 6/10
- **Reliability**: 7/10

## Sing-box Configuration
```json
{
  "type": "vmess",
  "tag": "proxy",
  "server": "1.1.1.1",
  "server_port": 443,
  "uuid": "uuid",
  "security": "auto",
  "transport": {
    "type": "ws",
    "path": "/path",
    "headers": {
      "Host": "example.com"
    }
  }
}
```
