# Security Architecture & Best Practices

ConfigStream implements a comprehensive, multi-layered security model to ensure the safety and integrity of aggregated proxy configurations. This document provides detailed information about security measures, threat models, and best practices.

---

## Table of Contents

1. [Security Overview](#security-overview)
2. [Threat Model](#threat-model)
3. [Defense Layers](#defense-layers)
4. [Proxy Validation](#proxy-validation)
5. [Content Integrity](#content-integrity)
6. [Infrastructure Security](#infrastructure-security)
7. [Data Protection](#data-protection)
8. [Supply Chain Security](#supply-chain-security)
9. [Monitoring & Incident Response](#monitoring--incident-response)
10. [User Security Guidelines](#user-security-guidelines)
11. [Responsible Disclosure](#responsible-disclosure)

---

## Security Overview

ConfigStream adopts a **defense-in-depth** approach with multiple security layers:

```
┌─────────────────────────────────────────────────────────┐
│                   SECURITY LAYERS                       │
├─────────────────────────────────────────────────────────┤
│  Layer 7: User Education & Guidelines                   │
├─────────────────────────────────────────────────────────┤
│  Layer 6: Monitoring & Anomaly Detection                │
├─────────────────────────────────────────────────────────┤
│  Layer 5: Content Integrity Validation                  │
├─────────────────────────────────────────────────────────┤
│  Layer 4: Active Security Scanning                      │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Input Validation & Sanitization               │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Network Security & Filtering                  │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Infrastructure & Supply Chain                 │
└─────────────────────────────────────────────────────────┘
```

### Key Security Principles

1. **Zero Trust**: All proxies are untrusted until proven safe
2. **Fail-Safe Defaults**: Deny-by-default for all security checks
3. **Defense in Depth**: Multiple layers of protection
4. **Graceful Degradation**: Continue operation even if optional security features unavailable
5. **Transparency**: Clear warnings when security features disabled

---

## Threat Model

### Adversaries

1. **Malicious Proxy Operators**
   - **Goal**: Intercept user traffic, steal credentials
   - **Methods**: MITM attacks, SSL stripping, DNS poisoning
   - **Mitigation**: Active security scanning, content validation

2. **Honeypot Operators**
   - **Goal**: Log user activity, identify users
   - **Methods**: Fake proxy servers, traffic logging
   - **Mitigation**: Honeypot detection, behavioral analysis

3. **Source Poisoners**
   - **Goal**: Inject malicious proxies into aggregation sources
   - **Methods**: Mass upload of bad configs, DoS attacks
   - **Mitigation**: Anomaly detection, source quality tracking

4. **State-Level Censors**
   - **Goal**: Block access to VPN aggregators
   - **Methods**: Traffic fingerprinting, protocol detection
   - **Mitigation**: TLS fingerprint randomization, protocol obfuscation

### Assets to Protect

1. **User Privacy**
   - Traffic metadata
   - Connection patterns
   - Geographic location

2. **Data Integrity**
   - Proxy configurations
   - GeoIP data
   - Test results

3. **System Availability**
   - Pipeline execution
   - Frontend access
   - API endpoints

### Attack Vectors

1. **Compromised Proxies**
   - MITM attacks on HTTPS connections
   - Credential harvesting
   - Malware injection

2. **Source Tampering**
   - Fake configuration injection
   - Denial of service via floods
   - Reputation attacks

3. **Supply Chain**
   - Compromised dependencies
   - Malicious PyPI packages
   - Container image tampering

4. **Infrastructure**
   - GitHub Actions abuse
   - Workflow injection
   - Secret extraction

---

## Defense Layers

### Layer 1: Infrastructure Security

**GitHub Actions Security**:
```yaml
permissions:
  contents: write
  pages: write
  # Minimal permissions - principle of least privilege
```

**No External Databases**:
- All state managed via Git artifacts
- Prevents injection attacks on persistent storage
- Version-controlled audit trail

**Immutable Infrastructure**:
- Runners destroyed after each run
- No persistent state between executions
- Fresh environment guarantees

---

### Layer 2: Network Security & Filtering

#### IP Blocklist

**Implementation**: `src/configstream/security/blocklist.py`

**Blocked Categories**:

1. **Private Networks** (RFC 1918)
   ```
   10.0.0.0/8
   172.16.0.0/12
   192.168.0.0/16
   127.0.0.0/8 (localhost)
   169.254.0.0/16 (link-local)
   ```

2. **TOR Exit Nodes**
   - Updated from public TOR directory
   - Prevents deanonymization attacks

3. **Known Honeypots**
   - ASN-based filtering
   - Behavioral indicators
   - Community-reported IPs

4. **Malicious ASNs**
   - Hosting providers known for abuse
   - ISPs with poor reputation
   - Bulletproof hosting networks

**Lookup Performance**:
- Current: O(n) linear search through 5000+ CIDR ranges
- Future: O(log n) with interval tree (planned for v1.4)

#### Port Filtering

**Blocked Ports**:
```python
DANGEROUS_PORTS = {
    22,    # SSH - likely hacked server
    23,    # Telnet - compromised host
    25,    # SMTP - spam relay
    3389,  # RDP - remote desktop (Windows malware)
    5900,  # VNC - remote access
}
```

#### DNS Rebinding Protection

**Implementation**: `src/configstream/security_validator.py:186-193`

**Protections**:
1. Detect hexadecimal IP encoding (`0x7f000001` = `127.0.0.1`)
2. Detect decimal IP encoding (`2130706433` = `127.0.0.1`)
3. Prevent DNS responses to private IPs
4. Block localhost redirects

---

### Layer 3: Input Validation & Sanitization

#### Trace ID Validation

**Purpose**: Prevent log injection attacks

**Implementation**:
```python
def validate_trace_id(trace_id: str) -> bool:
    # Only allow alphanumeric and hyphens
    return bool(re.match(r'^[a-zA-Z0-9\-]{1,64}$', trace_id))
```

**Attack Prevention**:
```python
# Malicious input
trace_id = "valid-id\nINFO:Fake log message"

# After validation
# Rejected - contains newline character
```

#### Config Sanitization

**Protocol-Specific Validation**:

1. **VMess**: JSON schema validation
2. **VLESS**: Reality parameter verification
3. **Shadowsocks**: Cipher suite whitelist
4. **Trojan**: Password complexity requirements
5. **Hysteria2**: Port range validation

**Port Validation**:
```python
if not (1 <= port <= 65535):
    raise ValueError(f"Invalid port: {port}")
```

**IP Format Validation** (Added in v1.3):
```python
try:
    ipaddress.ip_address(ip)
except ValueError:
    logger.debug(f"Invalid IP format: {ip}")
    return None
```

---

### Layer 4: Active Security Scanning

#### Honeypot Detection (Passive)

**Implementation**: `src/configstream/security/honeypot.py`

**Strategy**: Passive Intelligence (VirusTotal)

ConfigStream strictly avoids active scanning (e.g., port scanning) from GitHub Actions to prevent abuse complaints and IP bans.

**Detection Methods**:

1. **IP Reputation Lookup**
   - Queries VirusTotal API for the proxy IP.
   - Checks for malicious flags from 70+ security vendors.
   - Uses LRU caching to respect API rate limits.

2. **Behavioral Indicators** (Passive)
   - Subnet flooding detection (Anomaly Module).
   - High jitter/latency instability.

**Policy**:
- **No Active Port Scanning**: To prevent abuse complaints.
- **Fail Open**: If API is unreachable, defaults to "Safe" to avoid blocking legitimate traffic.
- **Caching**: Results cached for 1 hour.

#### TLS Fingerprint Randomization (uTLS)

**Implementation**: `src/configstream/security/utls_wrapper.py`

**Purpose**: Evade TLS-based fingerprinting

**How It Works**:

1. Standard Python SSL has predictable fingerprint
2. Advanced firewalls detect and block Python clients
3. uTLS mimics real browsers (Chrome, Firefox, iOS)

**Supported Fingerprints**:
- `chrome`: Mimics Chrome 120+
- `firefox`: Mimics Firefox 115+
- `ios`: Mimics Safari on iOS 17+
- `random`: Randomizes on each request

**Example**:
```python
# Standard Python SSL (DETECTABLE)
TLS 1.3, Cipher: TLS_AES_128_GCM_SHA256
Extensions: [0, 10, 11, 13, ...]

# uTLS Chrome Fingerprint (INDISTINGUISHABLE)
TLS 1.3, Cipher: TLS_AES_128_GCM_SHA256
Extensions: [0, 23, 65281, 10, 11, 35, ...]
```

**Requirements**:
- Go 1.20+ installed
- Automatic build on first use
- Graceful degradation if unavailable

**Security Note** (v1.3):
- Clear warning logged when uTLS unavailable
- Users informed about reduced fingerprint resistance

#### Shadowsocks Verification (Rust FFI)

**Implementation**: `src/configstream/security/ss_ffi.py`

**Purpose**: Ensure Shadowsocks configs are cryptographically valid

**Advantages of Rust Core**:
1. **Correctness**: Official implementation
2. **Performance**: 10× faster than Python
3. **Security**: Memory-safe language

**Verified Aspects**:
- Cipher suite validity
- Password entropy
- Plugin configuration
- AEAD vs. Stream cipher

**Example**:
```python
config = {
    "server": "1.2.3.4",
    "server_port": 8388,
    "password": "password",
    "method": "aes-256-gcm"
}

if verify_ss_rust(config):
    # Config is cryptographically sound
    proceed_with_testing()
```

**Security Note** (v1.3):
- Clear warning logged when Rust library unavailable
- Graceful fallback to basic validation

---

### Layer 5: Content Integrity Validation

#### MITM Detection

**Implementation**: `src/configstream/testers.py:323-354`

**Detection Methods**:

1. **Certificate Inspection**
   ```python
   suspicious_issuers = [
       "Fiddler",
       "GoProxy",
       "Charles Proxy",
       "Burp Suite",
       "mitmproxy",
   ]

   if any(issuer in cert.issuer for issuer in suspicious_issuers):
       proxy.security_issues.append("MITM_DETECTED")
       return False
   ```

2. **Certificate Chain Validation**
   ```python
   if not validate_cert_chain(cert):
       proxy.security_issues.append("INVALID_CERT_CHAIN")
       return False
   ```

3. **Self-Signed Certificate Detection**
   ```python
   if cert.issuer == cert.subject:
       proxy.security_issues.append("SELF_SIGNED")
       return False
   ```

#### HTML Injection Detection

**Implementation**: `src/configstream/testers.py:366-375`

**Test Procedure**:

1. **Control Request**
   ```python
   # Request known-clean page
   response = await session.get("https://example.com")
   original_html = response.text
   ```

2. **Pattern Detection**
   ```python
   injected_patterns = [
       r'<script[^>]*>',     # JavaScript injection
       r'<iframe[^>]*>',     # Frame injection
       r'<embed[^>]*>',      # Plugin injection
       r'onclick\s*=',       # Event handler injection
   ]

   for pattern in injected_patterns:
       if re.search(pattern, response.text, re.IGNORECASE):
           proxy.security_issues.append("HTML_INJECTION")
           return False
   ```

3. **Content-Length Comparison**
   ```python
   if abs(len(response.text) - len(original_html)) > 1000:
       # Significant content added
       proxy.security_issues.append("CONTENT_MODIFIED")
   ```

#### Header Preservation Check

**Implementation**: `src/configstream/testers.py:294-310`

**Tested Headers**:
```python
critical_headers = [
    "Host",
    "User-Agent",
    "Accept-Encoding",
    "Connection",
]

for header in critical_headers:
    if header not in response.request.headers:
        proxy.security_issues.append(f"HEADER_STRIPPED_{header}")
```

**Why It Matters**:
- Header stripping indicates MITM
- Missing headers can leak real IP
- Critical for privacy

---

### Layer 6: Monitoring & Anomaly Detection

#### Isolation Forest (Anomaly Detection)

**Implementation**: `src/configstream/anomaly.py`

**Purpose**: Detect source poisoning attacks

**How It Works**:

1. **Baseline Establishment**
   ```python
   # Historical data: typical proxy counts per source
   historical_counts = [50, 48, 52, 49, 51, 50, ...]

   # Train Isolation Forest
   model = IsolationForest(contamination=0.1)
   model.fit(historical_counts)
   ```

2. **Anomaly Scoring**
   ```python
   current_count = 500  # Sudden spike!
   score = model.decision_function([current_count])

   if score < -0.5:  # Threshold
       logger.warning(f"Anomaly detected: {source} returned {current_count} configs")
       # Reject or flag for manual review
   ```

3. **Adaptive Thresholds**
   ```python
   # Allow gradual growth but flag sudden spikes
   if current_count > 2 × max(historical_counts):
       flag_as_anomalous()
   ```

**Attack Scenarios Detected**:
- Mass config injection (DoS)
- Source compromise
- Data poisoning

#### Source Quality Tracking

**Implementation**: `src/configstream/source_quality.py`

**Tracked Metrics**:

```python
class SourceQuality:
    fetch_count: int           # Total fetches attempted
    success_count: int         # Successful fetches
    average_proxy_count: float # Expected proxy count
    diversity_score: float     # Geographic diversity (Gini)
    failure_streak: int        # Consecutive failures
    cooldown_until: datetime   # Backoff timestamp
```

**Adaptive Backoff**:
```python
def calculate_backoff(failures: int) -> int:
    """Exponential backoff with 48-hour cap"""
    base_delay = 600  # 10 minutes
    max_delay = 172800  # 48 hours

    backoff = base_delay × (2 ** failures)
    return min(backoff, max_delay)
```

**Example**:
```
Failure 1: 10 minutes
Failure 2: 20 minutes
Failure 3: 40 minutes
Failure 4: 80 minutes
...
Failure 10: 48 hours (capped)
```

#### Circuit Breaker Pattern

**Implementation**: `src/configstream/circuit_breaker.py`

**States**:
```
┌────────┐  5 failures  ┌────────┐  timeout  ┌──────────┐
│ CLOSED │─────────────▶│  OPEN  │──────────▶│HALF_OPEN │
└───▲────┘              └────────┘           └─────┬────┘
    │                                              │
    │ success                                      │ failure
    └──────────────────────────────────────────────┘
```

**Configuration**:
```python
CIRCUIT_BREAKER_THRESHOLD = 5      # failures to open
CIRCUIT_BREAKER_TIMEOUT = 60       # seconds before half-open
CIRCUIT_BREAKER_SUCCESS_THRESHOLD = 3  # successes to close
```

---

### Layer 7: User Education & Guidelines

See [User Security Guidelines](#user-security-guidelines) below.

---

## Supply Chain Security

### Dependency Management

**1. Version Pinning** (`pyproject.toml`):
```toml
[project.dependencies]
httpx = "==0.24.1"      # Exact version
pydantic = ">=2.0,<3.0" # Compatible range
```

**2. Hash Verification** (`requirements.txt`):
```
httpx==0.24.1 \
    --hash=sha256:abc123...
```

**3. Security Scanning**:
```bash
# Automated via GitHub Actions
pip-audit --requirement requirements.txt
```

**4. Renovate Bot**:
- Automated dependency updates
- Security patch notifications
- Automated testing before merge

### Code Integrity

**1. Signed Commits**:
```bash
git config --global commit.gpgsign true
```

**2. Protected Branches**:
- Require pull request reviews
- Require status checks to pass
- No force pushes to main

**3. GitHub Actions Security**:
```yaml
# Use hash instead of tag
uses: actions/checkout@8f4b7f84864484a7bf31766abe9204da3cbe65b3  # v3.5.0
```

### Container Security (Docker)

**Base Image**:
```dockerfile
FROM python:3.11-slim-bookworm
# Official Python image, minimal attack surface
```

**Non-Root User**:
```dockerfile
RUN useradd -m -u 1000 configstream
USER configstream
```

**Vulnerability Scanning**:
```bash
docker scan configstream:latest
```

---

## Data Protection

### Data at Rest

**1. SQLite Encryption** (Optional):
```python
# Using SQLCipher for encrypted databases
conn = sqlite3.connect("file:data.db?mode=ro&key=passphrase")
```

**2. File Permissions**:
```bash
chmod 600 data/*.db      # Owner read/write only
chmod 700 data/          # Owner full access
```

**3. Backup Encryption**:
```bash
tar czf - backup.db | gpg --encrypt --recipient key@example.com > backup.db.tar.gz.gpg
```

### Data in Transit

**1. HTTPS Everywhere**:
```python
# Enforce HTTPS for all fetches
if not url.startswith("https://"):
    logger.warning(f"Non-HTTPS source: {url}")
    # Skip or upgrade to HTTPS
```

**2. TLS 1.3 Minimum**:
```python
context = ssl.create_default_context()
context.minimum_version = ssl.TLSVersion.TLSv1_3
```

**3. Certificate Pinning** (Future):
```python
# Pin GitHub's certificate
PINNED_CERTS = {
    "github.com": "sha256/ABC123...",
}
```

### Secrets Management

**1. GitHub Secrets**:
```yaml
env:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
```

**2. Environment Variables**:
```bash
# Never commit to .env
echo ".env" >> .gitignore
```

**3. Secrets Rotation**:
- Rotate API keys every 90 days
- Use short-lived tokens when possible
- Revoke compromised credentials immediately

---

## Monitoring & Incident Response

### Security Logging

**Log Levels**:
```python
logger.warning("Honeypot detected: %s", ip)              # Security event
logger.error("MITM attempt blocked: %s", proxy.id)       # Active attack
logger.critical("Source poisoning detected: %s", source) # Major incident
```

**Structured Logging** (JSON):
```json
{
  "timestamp": "2025-11-21T10:30:00Z",
  "level": "WARNING",
  "event": "honeypot_detected",
  "ip": "1.2.3.4",
  "risk_score": 75,
  "trace_id": "abc-123"
}
```

### Alerting

**GitHub Actions Notifications**:
```yaml
- name: Notify on failure
  if: failure()
  uses: actions/github-script@v6
  with:
    script: |
      github.rest.issues.create({
        title: 'Pipeline security failure',
        body: 'Anomaly detected in pipeline run'
      })
```

### Incident Response Plan

**1. Detection**
- Automated anomaly alerts
- User reports
- Third-party security researchers

**2. Triage**
- Assess severity (Critical/High/Medium/Low)
- Identify affected users
- Determine attack vector

**3. Containment**
- Block malicious sources
- Revoke compromised credentials
- Roll back affected deployments

**4. Eradication**
- Patch vulnerabilities
- Update security rules
- Rebuild clean infrastructure

**5. Recovery**
- Restore from backups
- Verify integrity
- Resume normal operations

**6. Post-Mortem**
- Document timeline
- Analyze root cause
- Implement preventive measures
- Update runbooks

---

## User Security Guidelines

### ❌ DO NOT Use For

- **Banking or financial transactions**
- **Accessing sensitive personal information**
- **Confidential business communications**
- **Medical or legal matters**
- **Any activity requiring guaranteed privacy**

### ✅ Acceptable Use

- Casual web browsing
- Bypassing geo-restrictions
- Accessing blocked content
- Testing and development
- Educational purposes

### 🔐 Best Practices

1. **Always use HTTPS websites**
   - Green padlock in browser
   - `https://` in URL
   - Valid certificate

2. **Never enter passwords** for important accounts
   - Assume traffic may be logged
   - Use separate "throwaway" accounts if needed

3. **Avoid sensitive activities** entirely
   - No healthcare portals
   - No banking websites
   - No confidential work

4. **Use trusted VPN services** for critical needs
   - Commercial VPNs with privacy policies
   - Self-hosted VPNs on trusted servers
   - Corporate VPNs for work

5. **Be aware** of risks
   - Traffic may be logged or modified
   - Proxy operator can see all unencrypted traffic
   - MITM attacks are possible

6. **Verify proxy security scores**
   - Check `security_issues` field in JSON
   - Avoid proxies with warnings
   - Prioritize high-scored proxies

### Threat Awareness

**What Malicious Proxy Operators Can Do**:

1. **Intercept HTTP Traffic**
   ```
   User ──HTTP──▶ Proxy ──HTTP──▶ Website
                    │
                    ▼
              Log everything
   ```

2. **Modify Content**
   - Inject ads, malware, tracking scripts
   - Redirect to phishing sites
   - Strip security headers

3. **Harvest Credentials**
   - Capture login forms
   - Steal session cookies
   - Intercept API tokens

4. **Track Activity**
   - Log all visited websites
   - Build user profiles
   - Sell data to third parties

**How to Protect Yourself**:

1. **HTTPS Protects Content**: Proxy can see domains but not content
2. **DNS Over HTTPS**: Prevents DNS snooping
3. **VPN Over Proxy**: Double encryption
4. **Tor Over Proxy**: Maximum anonymity (slow)

---

## Responsible Disclosure

### Security Vulnerability Reporting

If you discover a security vulnerability in ConfigStream:

**DO**:
1. Email security details to: [Insert Contact Email]
2. Include detailed reproduction steps
3. Allow reasonable time for fix (90 days)
4. Coordinate disclosure timeline

**DON'T**:
1. Publicly disclose before patch available
2. Exploit vulnerability for personal gain
3. Access other users' data
4. Perform DoS attacks

### Bug Bounty

Currently, ConfigStream does not offer financial rewards but provides:
- Public acknowledgment (with permission)
- CVE credit if applicable
- GitHub Sponsors support option

### Hall of Fame

Security researchers who responsibly disclose vulnerabilities will be listed here:

- [Your Name] - [Vulnerability Type] - [Date]

---

## Security Checklist

### For Developers

- [ ] All dependencies pinned to specific versions
- [ ] Security scanning enabled in CI/CD
- [ ] No hardcoded secrets in code
- [ ] All user inputs validated and sanitized
- [ ] Error messages don't leak sensitive information
- [ ] Logging doesn't include PII or secrets
- [ ] Regular security audits performed
- [ ] Vulnerability disclosure process documented

### For Deployers

- [ ] Environment variables configured securely
- [ ] Database files have restricted permissions
- [ ] Logs are monitored for security events
- [ ] Backups are encrypted and tested
- [ ] Incident response plan documented
- [ ] Security contacts are up-to-date
- [ ] Rate limiting configured
- [ ] TLS certificates valid and renewed

### For Users

- [ ] Understand risks of using free public proxies
- [ ] Only use HTTPS websites
- [ ] Never enter sensitive credentials
- [ ] Check proxy security scores
- [ ] Use commercial VPNs for critical activities
- [ ] Report suspicious proxies
- [ ] Keep client software updated

---

## Security Roadmap

### v1.4 (Planned)

- [ ] Interval tree for O(log n) blocklist lookups (H-8)
- [ ] Enhanced MITM detection with CT log verification
- [ ] Automated certificate transparency monitoring
- [ ] WebAuthn support for admin authentication

### v1.5 (Planned)

- [ ] Machine learning-based honeypot detection
- [ ] Real-time reputation scoring
- [ ] Integration with threat intelligence feeds
- [ ] Blockchain-based proxy reputation system

### v2.0 (Future)

- [ ] End-to-end encrypted proxy configs
- [ ] Zero-knowledge proof of proxy validity
- [ ] Decentralized proxy aggregation
- [ ] Quantum-resistant cryptography

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CVE Database](https://cve.mitre.org/)

---

## Compliance & Standards

ConfigStream aims to align with:

- **GDPR**: Minimal data collection, no PII storage
- **OWASP ASVS**: Application Security Verification Standard
- **NIST SP 800-53**: Security and Privacy Controls
- **ISO 27001**: Information Security Management

---

**Last Updated**: 2025-11-21
**Version**: 1.3.0
**Security Contact**: [Insert Contact Information]

**Disclaimer**: ConfigStream is provided "as is" without warranties. Users assume all risks associated with using free public proxies. The maintainers are not responsible for proxy operator actions or user security incidents.
