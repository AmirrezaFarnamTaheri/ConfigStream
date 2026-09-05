# 07. Security & Privacy

ConfigStream operates in a hostile environment. We deal with circumvention tools, which attracts attention from censors and malicious actors. Security is not an afterthought; it is the foundation.

## The Threat Model

We defend against three primary threats:
1.  **Pollution Attacks**: Malicious actors flooding the repo with fake or blocked proxies to dilute the pool.
2.  **Honeypots**: State actors deploying logging nodes to track users.
3.  **Takedowns**: Hosting providers removing the repo due to abuse reports.

## Mitigation Strategies

### 1. Pollution Defense (Anomaly Detection)
We use statistical analysis to detect pollution.
*   **Subnet Analysis**: Spammers rarely have diverse IPs. They spin up 100 containers on one Vultr/DigitalOcean droplet. If we see >90% of a batch coming from one /24 subnet, we drop it.
*   **Sequential Ports**: Proxies on `8001, 8002, 8003` are almost always a port scan or a single multi-user node. We deduplicate these aggressively.

### 2. Honeypot Detection
State actors often deploy "fake" open proxies to log traffic.

Current implementation focusses on **passive** intelligence only:

*   **VirusTotal Integration**: Our honeypot guard (`src/configstream/security/honeypot.py`) uses `check_ip_reputation()` to check whether an IP has been flagged as malicious.
    *   If VirusTotal reports `malicious > 0`, the proxy is flagged and removed from the pool.
    *   If the `VT_API_KEY` is missing, we **log a warning** and fail open (no blocking), so operators are aware that honeypot reputation checks are effectively disabled.
*   **No Active Scanning**: Behavioral checks like open resolvers, echo servers, and header fingerprinting are **documented but not enabled** in production to respect a strict “Zero Abuse” policy and avoid port‑scan behaviour.
    *   The `check_common_honeypot_ports()` and `check_traffic_interception()` helpers are intentionally no-ops.
    *   Future work may add passive heuristics here (e.g. offline logs analysis) without probing the remote hosts.

### 3. Proxy Washing (IP Reputation)
Many "free" proxies are on IPs that are flagged by Cloudflare, Google, or other major providers. They connect, but they get CAPTCHAs or 403s.
*   **Concept**: We use the `ProxyWasher` (`src/configstream/intelligence/washer/core.py`).
*   **Mechanism**:
    *   `User -> [Dirty Proxy] -> [WARP Interface] -> Target`
*   **Implementation**:
    *   We generate a complex **Sing-box** configuration chain.
    *   The "Dirty Proxy" is the `outbound`.
    *   The `WARP` WireGuard tunnel is a second `outbound`.
    *   A `route` rule sends traffic from the Proxy outbound *into* the WARP outbound.
    *   The user gets a clean Cloudflare IP.
*   **Deterministic Key Assignment**: We map the Proxy ID to a specific WARP key using a hash (now based on SHA‑256) so that the same proxy always gets the same "Identity" (WARP key), preventing session churn.
*   **Candidate Selection**: When a WARP key pool is configured, we wash **all working proxies** (not only those tagged `dirty_ip`/`insecure`) to ensure that untagged but risky nodes still benefit from a clean egress IP.

### 4. TLS Fingerprinting (uTLS)
Standard Python `requests` or `ssl` libraries have a very distinct TLS fingerprint (JA3). Firewalls block this immediately.
*   **Solution**: We use **uTLS** (in our Go sidecar).
*   **Randomization**: We randomize the Client Hello packet to mimic:
    *   Chrome 120
    *   Firefox 118
    *   Safari 17
*   **Result**: We can successfully test and connect to proxies that block non-browser traffic.

### 5. Intranet Bridge
Some proxies are located inside restrictive domestic networks (e.g., Iran, China) and cannot reach the global internet directly, but *can* reach other domestic servers.
*   **Mechanism**: We chain these "Intranet" proxies through a "Bridge" proxy (a domestic server with international access, or a relay).
*   **Routing**: We create specific routing rules in `singbox.json` to tunnel traffic intelligently.

## Secrets Management

*   **No API Keys in Code**: We use GitHub Secrets.
*   **Gitleaks**: We run `gitleaks` in CI to catch accidental commits.
*   **Sanitization**: The pipeline strips `user`, `pass`, and `uuid` from logs. We only log the `hash(proxy)` for debugging.

## VirusTotal Integration

We cross-reference proxy IPs with VirusTotal's database.
*   **Metric**: "Malicious Votes".
*   **Threshold**: If > 3 vendors flag an IP as malware/botnet, we drop it.
*   **Caching**: We cache VT results for 7 days to respect API limits.
*   **Failure Mode**: If the API key is not configured or the API fails, we log a **warning** and fail open for that check only (the proxy may still be rejected by other validators such as blocklists or DNS rules).

## Anomaly Detection & Fail‑Open Policy

The `AnomalyDetector` (`src/configstream/anomaly.py`) protects against **pollution attacks** by modelling per‑source history and identifying massive spikes or drops.

*   For established sources, median absolute deviation / Z-score heuristics are used to detect outliers in batch size.
*   For new or small sources, simple heuristics guard against “sudden massive yield”.
*   **Failure Mode**: If the anomaly database is temporarily unavailable (e.g. SQLite error), we **fail open**:
    *   The source is **allowed** for this run.
    *   An error is logged with `DB Error (Fail Open)` so operators can fix the underlying storage problem.
    *   This prevents a transient DB issue from blocking **all** upstreams and silently collapsing the pipeline.

## Blocklist Management

The `BlocklistManager` (`src/configstream/security_validator.py`) maintains a merged blocklist from multiple sources:

*   **FireHol Level 1**: Known botnet C2 servers, spam sources, and malware IPs.
*   **VirusTotal Flagged IPs**: IPs with >3 malicious vendor flags (cached for 7 days).
*   **Custom Blocklist**: Operator-defined IPs/CIDRs via `DEFAULT_BLOCKLIST`.
*   **Thread Safety**: Uses `threading.Lock` in `__new__` for singleton instantiation (safe across async and threaded contexts).

## Log Sanitization

All log output is sanitized via `SecurityValidator.sanitize_log_message()`:

| Data Type | Example Raw | Sanitized Output |
|---|---|---|
| UUID | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` | `a1b2****-****-****-****-********7890` |
| Password | `password=MySecret123` | `password=****` |
| Key / Token | `token=eyJhbGciOi...` | `token=****` |
| IP (Internal) | `10.0.1.42` | `10.0.*.*` |

---

## 7. Cryptographic Release Signing & Zero-Trust Verification

**Target state:** strengthen integrity verification through the existing signed
artifact manifest. This is not a statement that every client format or browser
is already verified end-to-end.

### 7.1 Key Generation & Secret Isolation
- **Signing Key Pair**: Ed25519 256-bit asymmetric keypair generated via `cryptography.hazmat.primitives.asymmetric.ed25519`.
- **Private Key Isolation**: Inject `CS_SIGNING_PRIVATE_KEY_HEX` only into the GitHub Actions runner; never store it in code, logs, or artifacts.
- **Public Key Distribution**: Publish a pinned public key through the generated runtime configuration and verify the manifest in the browser.

### 7.2 Static-Hosting-Compatible Verification
GitHub Pages cannot attach custom per-file response headers. Therefore the
target is a signed `artifact_manifest.json` containing SHA-256 digests and a
detached Ed25519 manifest signature. Browser verification and any client
verification must consume that static artifact. A future header-based scheme
requires a separately deployed Worker or other configurable origin.

### 7.3 Cross-Language Signing Contract

The Python signer and browser verifier must consume exactly the same bytes.
Before treating browser verification as complete, define a versioned signing
envelope containing the canonical JSON encoding, timestamp representation and
byte order, signature algorithm, key identifier, and signature encoding. A
change to any field is a contract change and requires a compatibility decision.

Required evidence is a deterministic test vector generated by Python and
verified by browser WebCrypto, plus a negative test for an altered timestamp,
payload, signature, and key. Do not rely on two independent implementations
that each validate only their own fixtures.

**Rule**: Every new `logger.info()`, `logger.warning()`, or `logger.error()` call that includes URLs, credentials, or user data **must** be wrapped in `sanitize_log_message()`. This is enforced by code review and the `AGENTS.md` checklist.

## Security Checklist (for Contributors)

Before submitting code that touches security-sensitive areas:
1.  Are all new log statements sanitized?
2.  Are API keys read from environment variables (never hardcoded)?
3.  Does the code fail-open or fail-safe? (Document the choice.)
4.  Are new singletons using `threading.Lock` in `__new__`?
5.  Has `gitleaks` been run locally?

## Related Documentation

*   **[Security Concepts](../encyclopedia/glossary/security_concepts.md)** — Circuit Breaker, Adaptive Timeout, Fail-Open vs Fail-Safe, AEAD, Replay Protection, Entropy Analysis explained in depth.
*   **[Firewalls & Honeypots](../encyclopedia/security/firewall_honeypot.md)** — GFW, Iran, Russia censorship systems; honeypot detection techniques; how ConfigStream defends.
*   **[Networking Terms](../encyclopedia/glossary/networking_terms.md)** — TLS, SNI, DPI, obfuscation techniques referenced in the threat model.
*   **[Censorship Evasion](../../CENSORSHIP_EVASION.md)** — DNS hardening, shielding, TLS fingerprinting, BYOW, pipeline integration, testing.
*   **[Contributing](09-contributing.md)** — Coding standards and PR workflow for security-sensitive changes.
