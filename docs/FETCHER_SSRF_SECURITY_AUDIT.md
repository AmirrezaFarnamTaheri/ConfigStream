# FETCHER SSRF & SECURITY AUDIT

## Source Ingestion & SSRF Security Flowchart

```ascii
[consolidated_sources.txt]
       |
       v
[Producer.py: source_producer()]
       |--- Filter direct proxy strings
       |--- Replace ssconf:// with https://
       v
[Fetcher.py: fetch_multiple_sources()]
       |
       v
[Fetcher.py: _reject_source_dns()]
       |--- Resolve DNS using socket.getaddrinfo
       |--- Validate each IP against ipaddress.is_global (blocks 10.0.0.0/8, 127.0.0.0/8, 192.168.0.0/16, etc.)
       v
[DNS Rebinding Protection (Pinning)]
       |--- Pin resolved valid IP to URL (httpx stream)
       |--- Inject original hostname in 'Host' header
       v
[HTTPX Async Client] ---> Target Server
```

## Private Network Blocklist Enforcement Audit Table

| Component | Target Network | Blocked by Default? | Mechanism | Notes |
|---|---|---|---|---|
| `_reject_source_url` | `localhost`, `*.local`, `*.lan` | Yes | String suffix check | Prevents basic internal hostname resolution attempts. |
| `_reject_source_url` | `127.0.0.0/8` (Loopback) | Yes | `ip.is_global` | Handled via Python `ipaddress` module. |
| `_reject_source_url` | `10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12` (RFC 1918) | Yes | `ip.is_global` | Private IPv4 correctly identified and rejected. |
| `_reject_source_url` | `169.254.0.0/16` (Link-local) | Yes | `ip.is_global` | Blocked correctly. Important for AWS/GCP metadata SSRF. |
| `_reject_source_url` | Credentials embedded in URL | Yes | `parsed.username / parsed.password` | Rejected explicitly to prevent credential leaking in redirects. |
| `_reject_source_dns` | DNS Rebinding / TOCTOU | Yes | IP pinning | Resolves hostname, validates IP is global, rewrites URL to use IP literal, sets `Host` header. Defeats DNS rebinding. |
| `net.py` | `is_global_ip` | Yes | `ipaddress.ip_address(value).is_global` | Core validation helper. |

## Source URL Token & Credential Exposure Inventory

A scan of `consolidated_sources.txt` reveals the following patterns containing identifiable subscription tokens or tracking parameters that may expose user accounts if widely distributed:

- `https://apex.gaming-shop54.top/QXYR8Itk5Ll9oPHMixCwK/095f2d65-00b7-4760-9591-7599adc803d4/all.txt?name=...`
- `https://rss-node.com/link/vqOaWFJRfbYxpAhY?mu=1`
- `https://sub.idsvip.com/link/abcd1234?clash=1`
- Numerous paths contain pseudo-random strings acting as authentication UUIDs (e.g., `.../sub/dXNlcl...`).

*Recommendation: Users should be warned about committing personal subscription links with active tokens.*

## Adaptive Timeout & Circuit Breaker Resilience Evaluation

1. **Circuit Breaker Fast-fail:**
   `CircuitBreakerManager` evaluates per-host failure thresholds (default: 5 errors). If tripped, `fetch_from_source` returns an immediate "Circuit Breaker Open" failure, preventing stall propagation to the worker queue.
2. **Adaptive Timeout & Jitter:**
   The `AdaptiveTimeout` dynamically scales timeouts based on recent host latency. This prevents the pipeline from waiting on unresponsive nodes. A fixed ceiling (default 30s) prevents unbounded waits.
3. **Large Response Exhaustion:**
   Streaming chunk validation (`aiter_bytes()`) enforces `max_size` proactively. If the total bytes exceed the maximum limit (e.g., 10MB), the fetcher safely aborts without loading the entire payload into RAM.
4. **Binary Decoding Fallbacks:**
   The content is decoded with `.decode("utf-8", errors="ignore")`. There is no fallback to other encodings (e.g., `latin-1` or `base64` raw buffer inspection) if `utf-8` fails, but the `ignore` flag prevents crashes. This is a resilience trade-off prioritizing pipeline stability over extracting malformed binary strings.

## Security Hardening Roadmap

1. **Implement Strict Content-Type Validation:** Discard non-textual responses (e.g., `image/*`, `video/*`) *before* streaming bodies to save bandwidth and memory.
2. **Sanitize `consolidated_sources.txt`:** Implement a CI/CD check to strip query parameters like `token=` or UUID-like paths before publishing.
3. **Advanced Encoding Detection:** Instead of blindly ignoring UTF-8 errors, use `cchardet` or fallback to checking for base64 encoded strings in ASCII before dropping non-UTF-8 characters.
4. **Proxy Redirection Limit:** Enforce a hard timeout spanning *all* redirects, not just a per-request timeout, to mitigate infinite-redirect tarpits.
