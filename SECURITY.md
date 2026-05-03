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

#### Frontend (JavaScript)
- ✅ **XSS Protection**: DOMPurify library for HTML sanitization
- ✅ **CORS**: Restricted to localhost + GitHub Pages (configurable via ALLOWED_ORIGINS)
- ✅ **WebSocket Security**: Message validation with length limits and command whitelist
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
- ✅ **Artifact Security**: Pipeline outputs stored with 3-day retention
- ✅ **Permission Scoping**: Minimal permissions per job

### Data Security

#### Encryption
- **Stego Key**: Rotated every 6 hours via CI/CD (STEGO_KEY environment variable)
- **Admin API**: Protected with ADMIN_API_KEY. Production admin endpoints fail closed if this key is not configured.
- **Fernet Encryption**: Used for steganography feature (obfuscation only)

#### Privacy
- **No Telemetry**: No user tracking or analytics sent to external services
- **Local Processing**: All proxy testing done locally
- **No Cloud Dependencies**: Fully self-hosted solution
- **Insecure Proxy Retention**: Non-fatal policy rejections are retained and tagged so consumers can filter or discard downstream (malformed/invalid configs still drop).

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

### Latest Audit: 2026-02-08

**Overall Security Score: A (90/100)**

**Issues Fixed**:
- ✅ P0: Hardcoded encryption key removed (replaced with CI/CD injection)
- ✅ P0: CI/CD secret exposure fixed (HF_TOKEN via environment only)
- ✅ P1: CORS wildcard restricted (configurable allowed origins)
- ✅ P1: WebSocket message validation added
- ✅ P1: Admin endpoint authentication implemented
- ✅ P1: Parameter validation enhanced (base_version regex check)
- ✅ P2: Docker HEALTHCHECK added

**Verified Secure**:
- ✅ Subprocess command injection: **0 vulnerable calls** (6 audited, all safe)
- ✅ SQL injection: **0 vulnerabilities** (parameterized queries only)
- ✅ Path traversal: **Robust protection** (SAFE_PATH_PATTERN + os.path.commonpath)
- ✅ XSS: **DOMPurify integrated** (80+ innerHTML usages sanitized)

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
- Principle of least privilege
- Defense in depth

## Security Configuration

### Required Environment Variables
```bash
# Required for production admin endpoints:
export ADMIN_API_KEY="your-secret-admin-key"
export ALLOWED_ORIGINS="https://yourdomain.com"
export STEGO_KEY="your-base64-fernet-key"

# Optional security enhancements:
export WARP_KEY_POOL="key1,key2,key3"  # For proxy washing
export MAXMIND_LICENSE_KEY="your-key"   # For GeoIP lookups
```

### Deployment Checklist
- [ ] All secrets in environment variables (not files)
- [ ] ADMIN_API_KEY configured for admin endpoints
- [ ] ALLOWED_ORIGINS restricted to your domain
- [ ] STEGO_KEY rotated regularly (recommend: every 6 hours)
- [ ] Container running as non-root user
- [ ] Health checks enabled in orchestrator
- [ ] Logs monitored for suspicious activity
- [ ] Dependencies updated regularly (run pip-audit weekly)
- [ ] HTTPS enforced for all endpoints
- [ ] Rate limiting enabled at reverse proxy level

## Security Features by Component

### API Server (FastAPI)
- CORS restrictions with allowed origins list
- WebSocket message validation (1024 char limit)
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

**Last Updated**: 2026-02-14
**Next Security Audit**: Q3 2026
