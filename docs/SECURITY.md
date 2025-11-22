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
│  Layer 4: Active Security Scanning (Honeypot)           │
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
   - **Methods**: Fake proxy servers, traffic logging, banner injection
   - **Mitigation**: Active probing, signature matching, behavioral analysis

3. **Source Poisoners**
   - **Goal**: Inject malicious proxies into aggregation sources
   - **Methods**: Mass upload of bad configs, DoS attacks
   - **Mitigation**: Anomaly detection, source quality tracking

4. **State-Level Censors**
   - **Goal**: Block access to VPN aggregators
   - **Methods**: Traffic fingerprinting, protocol detection
   - **Mitigation**: TLS fingerprint randomization, protocol obfuscation

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

#### Config Sanitization

**Protocol-Specific Validation**:

1. **VMess**: JSON schema validation
2. **VLESS**: Reality parameter verification
3. **Shadowsocks**: Cipher suite whitelist
4. **Trojan**: Password complexity requirements
5. **Hysteria2**: Port range validation

---

### Layer 4: Active Security Scanning

#### Honeypot Detection (Hybrid)

**Implementation**: `src/go/tester` (Active) & `src/configstream/security/honeypot.py` (Passive)

**Strategy**: Active Probing + Passive Intelligence

**1. Active Probing (Go Engine)**
- **Canary Request**: The tester connects to a specific "Canary" endpoint (`CANARY_URL`).
- **Signature Verification**: The proxy sends a unique token. The Canary server responds with a signed HMAC of the token.
- **MITM/Replay Check**: If the proxy returns a valid HTTP 200 but the signature is invalid or missing, it indicates the proxy is intercepting (MITM) or serving cached/fake content.
- **Banner Grabbing**: Checks for suspicious banners (e.g., "MikroTik", "OpenSSH") on non-standard ports.

**2. IP Reputation (VirusTotal)**
- **Passive Lookup**: Checks proxy IP against VirusTotal (if API key present).
- **Fail-Open**: If API limits reached, defaults to trusting Active Probe results.

**Policy**:
- **Strict Mode**: If `strict_security=True`, any failure in Canary verification marks proxy as DEAD.
- **Active Scanning**: Performed safely from ephemeral runners.

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

#### Shadowsocks Verification (Rust FFI)

**Implementation**: `src/configstream/security/ss_ffi.py`

**Purpose**: Ensure Shadowsocks configs are cryptographically valid using the official Rust core.

---

### Layer 5: Content Integrity Validation

#### MITM Detection

**Implementation**: `src/configstream/testers.py`

**Detection Methods**:

1. **Certificate Inspection**
   ```python
   suspicious_issuers = [
       "Fiddler", "GoProxy", "Charles Proxy", "Burp Suite", "mitmproxy",
   ]
   ```

2. **Certificate Chain Validation**
   - Validates root CA trust chain.

3. **Self-Signed Certificate Detection**
   - Flags certs where issuer == subject.

#### HTML Injection Detection

**Test Procedure**:
1. Request known-clean page (e.g., Google 204, Cloudflare Trace).
2. Check response body for injected `<script>`, `<iframe>`, or ad/tracker signatures.
3. Verify Content-Length matches expected values.

#### Header Preservation Check

**Tested Headers**: `Host`, `User-Agent`, `Accept-Encoding`, `Connection`.
**Why It Matters**: Header stripping indicates tampering and can leak real IP.

---

### Layer 6: Monitoring & Anomaly Detection

#### Isolation Forest (Anomaly Detection)

**Implementation**: `src/configstream/anomaly.py`

**Purpose**: Detect source poisoning attacks (sudden massive influx of proxies from one source).

**How It Works**:
1. **Baseline**: Learns typical proxy counts per source.
2. **Scoring**: `IsolationForest` scores new batches.
3. **Rejection**: If score < threshold, the batch is flagged/rejected.

#### Source Quality Tracking

**Implementation**: `src/configstream/source_quality.py`

**Metrics**:
- **Yield Rate**: % of valid proxies.
- **Diversity**: Geo-distribution (Gini Index).
- **Consistency**: Failure streaks.

**Adaptive Backoff**: Exponentially increases fetch interval for failing sources (up to 48h).

---

## Data Protection

### Data at Rest

**1. Atomic Writes** (v1.3):
- All file writes use `AtomicFileWriter` (write temp -> fsync -> rename).
- Prevents corruption on crash/power loss.

**2. No Persistent Secrets**:
- Secrets exist only in GitHub Actions memory/env.
- No keys stored in repo.

### Data in Transit

**1. HTTPS Everywhere**: Enforced for all fetches.
**2. TLS 1.3**: Minimum version for connections.

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

---

**Last Updated**: 2025-05-27
**Version**: 1.3.2
**Disclaimer**: ConfigStream is provided "as is" without warranties. Users assume all risks associated with using free public proxies.
