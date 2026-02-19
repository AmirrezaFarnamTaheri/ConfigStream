# VLESS Protocol

VLESS (VMess Less) is a lightweight transport protocol designed to be faster and more flexible than its predecessor, VMess. It removes the encryption overhead, relying instead on the underlying transport security (TLS/XTLS) for confidentiality.

## Key Features
- **No Encryption**: Relies on TLS/XTLS, reducing CPU overhead.
- **Reality**: A modern camouflage mechanism that eliminates the need for SNI/domain ownership.
- **Fallback**: Can fallback to other services (like Nginx) if probing is detected.

## URI Format
```
vless://uuid@host:port?security=reality&sni=google.com&fp=chrome&pbk=public_key&sid=short_id&type=grpc&serviceName=grpc#Remarks
```

## Intelligence Score
- **Speed**: 10/10
- **Stealth**: 8/10 (With Reality)
- **Reliability**: 9/10

## Sing-box Configuration
```json
{
  "type": "vless",
  "tag": "proxy",
  "server": "1.1.1.1",
  "server_port": 443,
  "uuid": "uuid",
  "tls": {
    "enabled": true,
    "server_name": "google.com",
    "reality": {
      "enabled": true,
      "public_key": "pbk",
      "short_id": "sid"
    }
  }
}
```
