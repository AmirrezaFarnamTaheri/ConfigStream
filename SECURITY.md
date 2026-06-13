# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 3.0.x   | :white_check_mark: |
| 2.5.x   | :white_check_mark: |
| 2.0.x   | :x:                |
| 1.x.x   | :x:                |

## Security Best Practices

### Code Security

#### Backend (Python)
- ✅ **No SQL Injection**: All database queries use parameterized statements
- ✅ **No Command Injection**: All subprocess calls use list form (not shell=True)
- ✅ **Input Validation**: Comprehensive regex and type checking throughout
- ✅ **API Authentication**: ADMIN_API_KEY environment variable for admin endpoints
- ✅ **Secret Management**: All secrets via environment variables, never hardcoded
- ✅ **SSL Verification**: Certificate validation enabled (no verify=False)
- ✅ **Sanitized Logging**: High-risk proxy/config paths mask endpoints, URLs, tokens, UUIDs, passwords, keys, subprocess output, and exception text before logging

#### Logging Policy
- Python logs that may include proxy material, source URLs, parser input, subprocess output, hostnames, addresses, credentials, keys, UUIDs, tokens, or exception text must pass those values through `SecurityValidator.sanitize_log_message()` or a local wrapper such as `_safe_log_text()`, `_safe_proxy_ref()`, `_safe_source_ref()`, or `_sanitize_process_output()`.
- High-risk modules covered by static logging policy tests include parsers, converters, `dns_batch_resolver.py`, `tools/vwarp.py`, `security/rules.py`, `security/honeypot.py`, and `test_cache.py`.
- Parser extraction logs use generic dropped-line markers instead of raw config snippets.
- Vwarp process stdout/stderr logs are decoded safely, sanitized, and length-bounded before logging or storing failure details.
- Do not add f-string, `%`, or `.format()` logger messages that interpolate sensitive values in high-risk modules; use structured logger arguments after sanitizing the value.

#### Lab Live Testing
- `/api/lab/test-chain` is disabled by default in production.
- Production deployments must set `LAB_LIVE_TEST_ENABLED=true` before the endpoint is exposed.
- When enabled in production, requests must include a matching `ADMIN_API_KEY` payload field.
- The endpoint is rate-limited and rejects configs larger than `LAB_MAX_CONFIG_BYTES`.
- Submitted configs must include allowed outbound types only and cannot target localhost, internal hostnames, or private/non-global IP literals.

#### Source Fetching
- Source URLs are restricted to `http` and `https`.
- Source URLs cannot include credentials, localhost/internal hostnames, or private/non-global IP literals by default.
- Redirects are followed manually only after validating each `Location`; redirect depth is capped by `FETCH_MAX_REDIRECTS`.
- When `FETCH_VALIDATE_DNS=true`, source hostnames are resolved immediately before each fetch attempt, including redirect targets, and any private/non-global DNS answer is rejected before opening the HTTP stream.
- Signed frontend artifacts fail closed when WebCrypto is unavailable or public key material is missing/placeholder. Unsigned local content can still be parsed without verification.

#### Frontend Deploy Integrity
- GitHub Pages deploy generates `assets/js/runtime-config.js` from `CS_PUBLIC_KEY` and `STEGO_KEY` after copying frontend assets, leaving source-shaped JavaScript immutable.
- Deploy fails if required runtime keys are missing or if the public-key placeholder or stego placeholder remains in the Pages artifact.
- Workflow and Pages artifact validation enforce the frontend runtime-config guard so it cannot be removed from deploy without breaking validation.

#### Frontend (JavaScript)
- ✅ **XSS Protection**: DOMPurify library for HTML sanitization
- ✅ **CORS**: Restricted to explicit `ALLOWED_ORIGINS`; production rejects wildcard origin regex and disables browser credentialed CORS by default
- ✅ **WebSocket Security**: Message validation with length limits, command whitelist, connection cap, idle timeout, send timeout, and stale-connection cleanup
- ⚠️ **localStorage**: Used for non-sensitive data only (preferences, cache keys)
- ⚠️ **Console Logging**: Stripped in production builds (see .build-config.json)

#### Go (Proxy Tester)
- ✅ **Context Propagation**: Proper timeout handling with context.Context
- ✅ **Panic Recovery**: All goroutines have defer/recover
- ✅ **Error Handling**: Comprehensive error checking (17+ nil checks)
- ✅ **Thread Safety**: No shared mutable state, proper synchronization

### Deployment Security

#### Docker
- ✅ **Non-root User**: Container runs as 'runner' user (UID 1000)
- ✅ **Health Checks**: HEALTHCHECK instruction validates container health
- ✅ **Minimal Base**: Uses python:3.12-slim for reduced attack surface
- ✅ **Dependency Pinning**: All versions locked in requirements.txt

#### CI/CD (GitHub Actions)
- ✅ **Secret Management**: All secrets in GitHub Secrets, not environment
- ✅ **No Command-line Secrets**: Tokens passed via environment variables only
- ✅ **Artifact Security**: Pipeline and Pages artifacts stored with 30-day retention
- ✅ **Permission Scoping**: Minimal permissions per job

### Data Security

#### Encryption
- **Stego Key**: Rotated every 6 hours via CI/CD (STEGO_KEY environment variable)
- **Admin API**: Protected with ADMIN_API_KEY. Production admin endpoints fail closed if this key is not configured.
- **Lab Live Test API**: Disabled by default in production. When explicitly enabled, requests must include a matching `ADMIN_API_KEY` payload field and remain subject to rate and request-size limits.
- **Fernet Encryption**: Used for steganography feature (obfuscation only)

#### Privacy
- **No Telemetry**: No user tracking or analytics sent to external services
- **Local Processing**: All proxy testing done locally
- **Log Privacy**: Runtime logs must not expose proxy endpoints, credentials, UUIDs, source tokens, raw configs, or subprocess output without sanitizer masking.
- **No Cloud Dependencies**: Fully self-hosted solution
- **Insecure Proxy Retention**: Non-fatal policy rejections are retained and tagged so consumers can filter or discard downstream (malformed/invalid configs still drop).
- **Private IP Policy**: By default, `ALLOW_PRIVATE_IPS=false` during proxy validation to prevent testing against internal infrastructure. Source fetching also blocks private networks by default.

## Reporting a Vulnerability

### Process
1. **DO NOT** open a public issue for security vulnerabilities
2. Email security details to: [Repository Owner Email]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

### Response Timeline
- **Initial Response**: Within 48 hours
- **Severity Assessment**: Within 1 week
- **Fix Timeline**:
  - Critical: 1-3 days
  - High: 1-2 weeks
  - Medium: 1 month
  - Low: Next release cycle

### Disclosure Policy
- Coordinated disclosure after fix is released
- Credit given to reporter (if desired)
- Security advisory published in GitHub Security Advisories

## Security Audit Results

### Latest Audit: 2026-05-13

**Overall Security Score: A (95/100)**

**Issues Fixed**:
- ✅ P0: Hardcoded encryption key removed (replaced with CI/CD injection)
- ✅ P0: CI/CD secret exposure fixed (HF_TOKEN via environment only)
- ✅ P0: DNS Rebinding protection implemented via `SecurityTransport` IP pinning
- ✅ P1: CORS wildcard removed from production defaults; production uses explicit allowed origins
- ✅ P1: WebSocket message validation added
- ✅ P1: Admin endpoint authentication implemented
- ✅ P1: Parameter validation enhanced (base_version regex check)
- ✅ P2: Docker HEALTHCHECK added

**Verified Secure**:
- ✅ Subprocess command injection: **0 vulnerable calls** (6 audited, all safe)
- ✅ SQL injection: **0 vulnerabilities** (parameterized queries only)
- ✅ Path traversal: **Robust protection** (SAFE_PATH_PATTERN + os.path.commonpath)
- ✅ XSS: **DOMPurify integrated** with project-owned runtime `innerHTML` assignments removed from frontend modules; rich content flows through safe DOM construction or sanitized DOM fragments.

**Known Considerations**:
- ⚠️ console.log in production: Stripped via build process (.build-config.json)
- ⚠️ localStorage: Contains only non-sensitive data (preferences, cache)
- ⚠️ Stego encryption: Obfuscation only (client-side visible key)

### Threat Model

**Assumed Attacker Capabilities**:
- Network-level observer (can see requests/responses)
- Malicious proxy provider (can return crafted configs)
- Client-side attacker (JavaScript in browser)

**Out of Scope**:
- Physical access to server
- GitHub account compromise
- Supply chain attacks on dependencies
- Browser/OS zero-days

**Mitigations**:
- Input validation at all boundaries
- Output encoding for all dynamic content
- Defense in depth
- **DNS Rebinding Protection**: Pre-connect resolution and IP pinning during fetching

## Security Configuration

### Required Environment Variables
```bash
# Required for production admin endpoints:
export ADMIN_API_KEY="your-secret-admin-key"
export ALLOWED_ORIGINS="https://yourdomain.com"
export CORS_ALLOW_CREDENTIALS="false"
export STEGO_KEY="your-base64-fernet-key"

# Optional security enhancements:
export WARP_KEY_POOL="key1,key2,key3"  # For proxy washing
export MAXMIND_LICENSE_KEY="your-key"   # For GeoIP lookups
export ALLOW_PRIVATE_IPS="false"       # Default: false
```

### Deployment Checklist
- [ ] All secrets in environment variables (not files)
- [ ] ADMIN_API_KEY configured for admin endpoints
- [ ] ALLOWED_ORIGINS restricted to your domain
- [ ] STEGO_KEY rotated regularly (recommend: every 6 hours)
- [ ] Container running as non-root user
- [ ] Health checks enabled in orchestrator
- [ ] Logs monitored for suspicious activity without exposing raw proxy, token, credential, UUID, or key material
- [ ] Dependencies updated regularly (run pip-audit weekly)
- [ ] HTTPS enforced for all endpoints
- [ ] Rate limiting enabled at reverse proxy level

## Security Features by Component

### API Server (FastAPI)
- CORS restrictions with explicit allowed origins list and no production wildcard regex
- WebSocket message validation (1024 char limit)
- WebSocket lifecycle limits for max connections, idle timeout, send timeout, and stale cleanup
- Admin endpoint authentication
- Parameter validation (regex + length limits)
- Path traversal protection (commonpath validation)
- Structured error messages (no stack traces in production)

### Frontend (JavaScript)
- DOMPurify for HTML sanitization
- CSP-ready architecture
- SRI-compatible asset loading
- Service Worker for offline support
- Differential updates to reduce attack surface

### Proxy Tester (Go)
- Timeout enforcement (context.WithTimeout)
- Goroutine leak prevention
- Panic recovery in all workers
- Connection limits (MaxWorkers=15)
- Retry limits (MaxRetries=5)

### Pipeline (Python)
- Circuit breaker for failing sources
- Rate limiting for external APIs
- Quality tracking with anomaly detection
- Blocklist integration (FireHol Level 1)
- Security validation (VirusTotal integration)
- **SecurityTransport**: DNS rebinding protection and IP pinning for all source fetches.
- Optional Shadowsocks-Rust FFI validation only when an operator supplies a
  local binary and matching `SS_LIB_SHA256`; otherwise Python validation remains
  authoritative, and a configured hash mismatch fails closed.

## Compliance

### OWASP Top 10 (2021)
- ✅ A01 Broken Access Control: Admin API authentication
- ✅ A02 Cryptographic Failures: No hardcoded secrets
- ✅ A03 Injection: Parameterized queries, no shell=True
- ✅ A04 Insecure Design: Defense in depth architecture
- ✅ A05 Security Misconfiguration: Secure defaults
- ✅ A06 Vulnerable Components: Regular dependency updates
- ✅ A07 Auth Failures: API key authentication
- ✅ A08 Data Integrity: Input validation
- ✅ A09 Logging Failures: Comprehensive logging
- ✅ A10 SSRF: Proxy testing is the intended functionality

### License Compliance
- All dependencies properly attributed
- GPL compatibility verified
- No proprietary code included
- Third-party licenses in LICENSES/ directory

## Contact

For security-related questions or concerns:
- Email: [Security Contact]
- PGP Key: [PGP Fingerprint]
- Response Time: 48 hours maximum

---

**Last Updated**: 2026-05-13
**Next Security Audit**: Q4 2026
