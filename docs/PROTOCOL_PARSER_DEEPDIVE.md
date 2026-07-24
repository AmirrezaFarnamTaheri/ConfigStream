# Protocol Parser Deep-Dive & Edge-Case Vulnerability Audit

## 1. Parser Protocol Coverage Matrix

| Protocol | Implementation | Scheme Supported | Parsed Through | Credential Standard |
|----------|----------------|------------------|----------------|---------------------|
| VLESS | `vless.py` | `vless://` | URL Scheme | UUID |
| VMess | `vmess.py` | `vmess://` | Base64 + JSON | UUID |
| Trojan | `trojan.py` | `trojan://`, `trojan-go://` | URL Scheme | Password (in username field) |
| Shadowsocks | `shadowsocks.py` | `ss://` | Base64 / URL Scheme | Method:Password |
| Shadowsocks 2022 | `shadowsocks.py` | `ss2022://` | URL Scheme | Method:Password |
| SSR | `ssr.py` | `ssr://` | Base64 | Password |
| Hysteria | `others.py` | `hysteria://` | URL Scheme | Password |
| Hysteria2 | `others.py` | `hysteria2://`, `hy2://` | URL Scheme | Password |
| TUIC | `others.py` | `tuic://` | URL Scheme | UUID + Password |
| WireGuard | `others.py` | `wg://`, `wireguard://`, `exclave://` | URL Scheme | Private Key |
| Xray | `others.py` | `xray://` | URL Scheme | UUID |
| Snell | `others.py` | `snell://` | URL Scheme | Password |
| Brook | `others.py` | `brook://` | URL Scheme | Password |
| Juicity | `others.py` | `juicity://` | URL Scheme | UUID |
| SSH | `others.py` | `ssh://` | URL Scheme | Username + Password |
| Naive | `generic.py` | `naive+https://` | URL Scheme | Username + Password |
| V2Ray JSON | `generic.py` | `{...}` | JSON | Varies (VMess/VLESS/SS/Trojan) |
| SOCKS/HTTP | `generic.py` | `socks://`, `http://`, etc. | URL Scheme / Naked | Username + Password |

## 2. Base64 & Credential Recovery Security Table

### Base64 Decoding Robustness
- **Implementation Location**: `decoders.py` (`validate_b64_input`, `safe_b64_decode`).
- **Missing Padding**: Automatically corrected (`pad = len(cleaned) % 4; if pad: cleaned += "=" * (4 - pad)`).
- **Trailing Garbage**: Handled efficiently by stripping non-standard Base64 characters from ends while rejecting inputs containing > 5% internal noise.
- **URL-safe Conversion**: Auto-replaces `-` and `_` with `+` and `/`.
- **Validation Fallback**: Attempts `validate=True` first, gracefully degrades to `validate=False` if plausible.

### Credential Recovery Logic
Parsers actively recover missing primary credentials from query parameters before dropping the proxy:
- **Shadowsocks**: If password is empty, scans `password`, `psk`, `pass`, `pwd` in `details`.
- **Trojan**: Falls back to password, then checks `password`, `pass`, `pwd`, `token`, `uuid`, `id`.
- **VLESS**: Scans `uuid`, `id`, `user`, `userid`, `uid` in parameters if omitted from user info part.
- **WireGuard**: Recovers `private_key` from URL username or aliases (`private-key`, `privateKey`).
- **TUIC**: Implicitly falls back to using UUID as the password if password query param is missing.

## 3. Malformed Input Fuzzing Scenarios & Drop Rate Handling

- **Mandatory Field Enforcement**: 
  - All parsers enforce returning `None` (dropping) if mandatory connection fields (UUID, password, host, port) are missing.
  - Port boundaries (1-65535) and hostname limits (<= 255 chars) are strictly enforced.
- **Shadowsocks Method Validation**: 
  - `shadowsocks.py` successfully blocks pseudo/invalid methods: `{"ss", "shadowsocks", "", "null", "default", "cipher", "aes", "chacha20"}`.
- **Drop Rate Logging**:
  - `shadowsocks.py`, `vmess.py`, and `others.py` comprehensively use `logger.debug` and `logger.warning` to log drop reasons (e.g., "Shadowsocks proxy dropped: no password after fallback check").
  - `vless.py` lacks explicit trace logs for drop scenarios, relying instead on a broad exception catch.

## 4. Edge-Case Vulnerability Findings

1. **VLESS Broad Exception Swallowing**: `vless.py` ends with a broad `except Exception` that returns `None` but uses a suppressed exception trace. This hides parsing vulnerability crashes (e.g., malformed IPv6 brackets).
2. **SSR Incomplete Parameter Extraction**: `ssr.py` partitions by `/?`. This will fail to extract parameters if the fragment just starts with `?` without the leading slash, hiding malicious payload injections in parameters.
3. **Generic Naked IP Exploits**: `generic.py` naked IP regex doesn't natively defend against malformed IPv6 injections, relying entirely on `ipaddress.ip_address` which throws `ValueError` instead of a sanitized drop.

## 5. Code Hardening Patches (Recommendations)

1. **Improve VLESS Logging**: Replace `logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)` in `vless.py` with explicit check failures (e.g., `logger.debug("VLESS dropped: Missing UUID or Host")`).
2. **Fix SSR Query Extraction**: Update `ssr.py` partitioning from `partition("/?")` to handle both `/?` and `?` as valid parameter boundaries.
3. **Strict Validation for Generic Hostnames**: Consolidate `_HOSTNAME_PATTERN` in `generic.py` to prevent Server-Side Request Forgery (SSRF) and ensure strict sanitization for all unquoted inputs before they reach database insertion.
