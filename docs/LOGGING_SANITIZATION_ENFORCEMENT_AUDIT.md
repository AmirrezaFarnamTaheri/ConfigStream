# Logging Sanitization Enforcement Audit

## Logging Sanitization Architecture Flowchart

```ascii
+-------------------+       +-----------------------+       +-------------------+
|                   |       |   SecurityValidator   |       |                   |
|  Unsafe Context   | ----> | .sanitize_log_message | ----> |   Safe Context    |
| (Raw config, IPs) |       | (Regex Sequence mask) |       |  (Cleaned logs)   |
+-------------------+       +-----------------------+       +-------------------+
                                       |
                                       v
                        +-------------------------------+
                        | 1. UUID Masking               |
                        | 2. URL UserInfo Masking       |
                        | 3. Inline Secret Masking      |
                        | 4. Query Params Masking       |
                        | 5. Auth Headers Masking       |
                        | 6. Bearer Token Masking       |
                        | 7. Base64 String Masking      |
                        | 8. IPv4 / IPv6 Masking        |
                        +-------------------------------+
```

## Masking Regex & Token Protection Matrix

| Data Type | Regex Variable | Description | Masked Result |
| :--- | :--- | :--- | :--- |
| UUID | `_LOG_UUID_RE` | Matches standard UUID formats (VMess/VLESS) | `[UUID]` |
| URL UserInfo | `_LOG_USERINFO_RE` | Matches `://user:pass@host` | `prefix:[MASKED]@` |
| Inline Secrets | `_LOG_INLINE_SECRET_USERINFO_RE` | Matches `pass|token|secret:value@` | `prefix:[MASKED]@` |
| Query Params | `_LOG_QUERY_SECRET_RE` | Matches `token=`, `key=`, `secret=`, etc. | `param=[MASKED]` |
| Auth Headers | `_LOG_AUTH_HEADER_RE` | Matches `Authorization: Bearer ...` | `header: [MASKED]` |
| Bearer Tokens | `_LOG_BEARER_RE` | Matches standalone `Bearer ...` tokens | `Bearer [MASKED]` |
| Base64 Strings| `_LOG_BASE64_RE` | Matches 20+ char base64 sequences | `[BASE64]` |
| IP Addresses | `_LOG_IPV4_RE` / `_LOG_IPV6_RE` | Matches IPv4 and IPv6 patterns | `[IP]` |

## Parser & Server Endpoint Log Leak Verification Table

The automated AST-based tests ensure no unmasked variables enter log functions.

| Component | Test Validation | Status |
| :--- | :--- | :--- |
| **AST AST-Checker** | Validates static sanitization of high-risk paths (`test_high_risk_logging_surfaces_use_static_sanitization_policy`) | Pass ✅ |
| **Singbox Converter** | Enforces masking of endpoint and tokens when UUID is missing | Pass ✅ |
| **DNS Resolver** | Ensures failing hostname exceptions mask IPs and secrets | Pass ✅ |
| **VWarp Tools** | Ensures output bounding and IP/token sanitization | Pass ✅ |
| **Security Rules** | Enforces IP sanitization during address validation rules | Pass ✅ |
| **Honeypot Logic** | Verifies token and IP sanitization when reputation checks fail | Pass ✅ |
| **Test Cache** | Enforces endpoint IP masking upon cache hits/misses | Pass ✅ |
| **Shadowsocks Parser**| Prevents configuration leaks in drop logs | Pass ✅ |
| **OpenVPN Parser** | Verifies that invalid remote hosts mask secrets and IPs | Pass ✅ |
| **Extraction** | Masks samples when dropping invalid configuration lines | Pass ✅ |

## Sanitization Performance Overhead Assessment

1. **Regex Execution**: `sanitize_log_message` applies 9 sequential regex operations. This occurs per-message. While the regexes are compiled once globally (`re.compile`), the sequential execution in the hot path is computationally heavy during massive log ingestion.
2. **Base64 Matching**: `_LOG_BASE64_RE` (matching `[A-Za-z0-9+/]{20,}={0,2}`) is broad and can induce performance lag (regex backtracking/eval) on long strings. 
3. **Bound Limits**: The vwarp output is actively bounded before sanitization (`_sanitize_process_output`), but other arbitrary string conversions do not truncate *before* regex execution.

## Hardening Recommendations

1. **Pre-Filtering Constraints**: Check for the existence of fast-search characters (e.g., `://`, `@`, `=`, `bearer`, `.`, `:`) before executing the full regex suite to bypass overhead on obviously safe strings.
2. **Length Bounding Pre-Regex**: Truncate exceedingly long logs *before* passing them to `sanitize_log_message` to avoid pathological regex evaluation times.
3. **Structured Logging**: Transition from regex-based string masking to structured logging. Pass sensitive parameters as isolated kwargs and have a custom logging formatter omit or hash them, entirely sidestepping the overhead of regex parsing.
4. **Custom Logging Wrapper**: Replace the AST-based test enforcement with an actual runtime wrapper around `logger` that forces sanitization on all outbound logging, preventing any future leak vectors that bypass AST testing.
