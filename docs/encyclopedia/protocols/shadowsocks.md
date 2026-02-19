# Shadowsocks

Shadowsocks is a secure SOCKS5 proxy designed to protect internet traffic. It uses AEAD ciphers for authentication and encryption.

## Key Features
- **Simplicity**: Very easy to deploy and use.
- **AEAD**: Authenticated encryption (e.g. AES-256-GCM, Chacha20-Poly1305).
- **Plugins**: Supports obfuscation plugins (v2ray-plugin, obfs).

## URI Format
```
ss://method:password@host:port#Remarks
```
Or Base64 encoded: `ss://BASE64#Remarks`

## Intelligence Score
- **Speed**: 9/10
- **Stealth**: 5/10 (without plugins), 8/10 (with v2ray-plugin)
- **Reliability**: 7/10

## Sing-box Configuration
```json
{
  "type": "shadowsocks",
  "tag": "proxy",
  "server": "1.1.1.1",
  "server_port": 8388,
  "method": "aes-256-gcm",
  "password": "password"
}
```
