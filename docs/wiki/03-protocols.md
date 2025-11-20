# 03. Protocol Deep Dive

This document explains how ConfigStream handles the parsing, validation, and testing of modern censorship-resistant proxy protocols.

## Supported Protocols

| Protocol | Parsing Logic | Validation | Test Client | Security |
| :--- | :--- | :--- | :--- | :--- |
| **VLESS** | `parsers.py:_parse_vless` | Check UUID, Address, Port. If `security=reality`, check `pbk`. | Sing-box | uTLS |
| **VMess** | `parsers.py:_parse_vmess` | Decode Base64 -> JSON. Validate `id`, `add`, `port`, `aid`. | Sing-box | uTLS |
| **Trojan** | `parsers.py:_parse_trojan` | `trojan://password@host:port`. Ensure password exists. | Sing-box | uTLS |
| **Shadowsocks** | `parsers.py:_parse_ss` | Decode Base64 (SIP002). Validate cipher & password. | Sing-box | **Rust FFI** |
| **Hysteria 2** | `parsers.py:_parse_hysteria2` | `hy2://`. Check `ports` (hopping), `obfs` (salamander). | Sing-box | N/A |
| **WireGuard** | `parsers.py:_parse_wireguard` | Check keys. Parse `reserved` bytes (Base64/CSV) for WARP. | Sing-box | N/A |
| **OpenVPN** | `parsers.py:_parse_openvpn` | Regex scan for `remote host port` and `BEGIN CERTIFICATE`. | N/A | N/A |

## Advanced Protocol Features

### 1. Hysteria 2 Port Hopping
Hysteria 2 supports hopping between a range of ports to evade blocking.
-   **Parsing**: We look for the `ports` query parameter (e.g., `ports=80,443,10000-20000`).
-   **Validation**: We regex match the range format `^[\d,\-]+$`.
-   **Testing**: Sing-box handles the hopping logic internally during the connection test.

### 2. WireGuard & Cloudflare WARP
Cloudflare WARP uses a modified WireGuard protocol distinguished by reserved bytes.
-   **Reserved Bytes**: ConfigStream parses the `reserved` field from URL parameters. It supports:
    -   **Base64**: `reserved=eyJ...`
    -   **CSV**: `reserved=12,34,56`
    -   **Bracketed**: `reserved=[12, 34, 56]`
-   **Output**: Converted to the correct integer array format for Sing-box JSON.

### 3. Shadowsocks Verification (Rust FFI)
Pure Python implementations of Shadowsocks crypto (e.g., `chacha20-poly1305`) are slow and CPU-intensive.
-   **Architecture**: We compile a Rust dynamic library (`libss_checker.so` / `.dll`) that links against the official `shadowsocks-rust` crate (simulated in PoC).
-   **FFI**: Python uses `ctypes` to pass the configuration JSON to the Rust function `verify_shadowsocks`.
-   **Benefit**: 10x-100x faster validation of cryptographic parameters.

## Security & Obfuscation

### TLS Fingerprint Randomization (uTLS)
Standard Python `ssl` or `requests` libraries have a fixed, easily identifiable TLS Client Hello fingerprint (JA3). Advanced firewalls block this.
-   **Solution**: We use a **Go Sidecar** (`src/go/utls_client`).
-   **Mechanism**:
    1.  Python spawns the Go binary.
    2.  Go binary uses `uTLS` to generate a randomized Hello (Chrome, Firefox, iOS).
    3.  Go performs the handshake and reports success/failure to Python.
-   **Integration**: Used primarily for direct checks or verifying if a proxy supports specific fingerprints.

### Honeypot Detection
Malicious proxies (honeypots) often expose themselves by running standard services on the same IP.
-   **Active Scanning**: Before listing a proxy, we asynchronously scan:
    -   **Port 22 (SSH)**: Indicates a hacked server or administration interface.
    -   **Port 23 (Telnet)**: Highly suspicious, indicates insecure IoT device or trap.
    -   **Port 3389 (RDP)**: Windows Server, potential compromise.
-   **Logic**: If any "management" port is open to the public, the proxy is flagged as `UNSAFE`.

## VLESS REALITY
**REALITY** eliminates the need for a signed certificate by mimicking a target website (SNI).
-   **Validation**: We strictly check for `pbk` (Public Key) and `sid` (Short ID).
-   **Flow**: We support `xtls-rprx-vision` flow control parsing.
