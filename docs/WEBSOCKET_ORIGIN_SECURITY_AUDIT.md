# WebSocket Origin & Real-time Security Audit

**Target:** `src/configstream/server/ws.py` & `src/configstream/models.py`  
**Focus:** WebSocket Origin Security, CSWSH Mitigations, and Hash Stability

---

## 1. WebSocket Origin Validation & CSWSH Security Flowchart

The following flowchart outlines the logic utilized in `_is_allowed_origin` to prevent Cross-Site WebSocket Hijacking (CSWSH).

```text
      [WebSocket Request]
             |
             v
     [Has Origin Header?]
      /                \
    No                 Yes
    |                   |
 [Reject]   [Split ALLOWED_ORIGINS by ',']
                        |
              [Contains wildcard '*'?]
              /                      \
            Yes                      No
             |                        |
    [Log error, strip '*']            |
             \                       /
              \                     /
             [Match explicit list?]
             /                    \
           Yes                    No
            |                      |
        [Accept]        [ALLOWED_ORIGIN_REGEX defined?]
                        /                             \
                      No                              Yes
                      |                                |
                   [Reject]               [Regex parses without error?]
                                          /                           \
                                        No                            Yes
                                        |                              |
                               [Log error, Reject]              [Matches Regex?]
                                                                /              \
                                                              Yes               No
                                                               |                |
                                                            [Accept]         [Reject]
```

## 2. Allowed Origin & Regex Safety Verification Table

| Validation Type | Mechanism | Edge Case Handling | Security Status |
|-----------------|-----------|--------------------|-----------------|
| **Missing Origin** | Returns `False` | Blocks empty/missing headers (`if not origin:`). | **Pass** (CSWSH mitigation) |
| **Allowed List** | `origin in allowed` | Strips whitespace. Removes insecure wildcard `*` with a logged error. | **Pass** |
| **Empty String** | Evaluated as missing | Fails initial truthiness check securely. | **Pass** |
| **Regex Match** | `re.fullmatch(pattern, origin)` | Bounded by a try/catch `re.error` block. Graceful rejection on broken regex. | **Pass** (Safe default) |

## 3. Deterministic Proxy ID Hash Stability Audit

**File Analyzed:** `src/configstream/models.py` (`Proxy.id` property)

- **Composite Key Generation:** The hash key is built deterministically as `f"{proto}|{addr}|{port}|{credential}"`.
- **Normalization:** 
  - `proto` is canonicalized.
  - `addr` is stripped and converted to lowercase.
  - `credential` iterates through a fallback priority list (`uuid`, `password`, `private_key`, etc.), ensuring the most secure material available is used.
- **Hash Function:** Applies `hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]`. 
- **Security Posture:** 
  - Fixed an earlier issue where raw UUIDs were emitted (breaking IDs and potentially leaking exact UUID parameters).
  - The deterministic approach ensures consistent, deduplicable 16-character hex hashes regardless of equivalent properties.

## 4. Malformed Input & Error Boundary Handling Assessment

- **Invalid Regular Expressions:** Handled properly via Python's `re.error` block. The system degrades securely by logging `"ALLOWED_ORIGIN_REGEX is invalid..."` and reverting to default-deny, preventing crashes.
- **Log Injection Protections:** Disallowed origin headers are sanitized using `SecurityValidator.sanitize_log_message` before logging, neutralizing malicious payloads inside the `Origin` header.
- **Payload Boundaries:** Implements an aggressive limit on payload size (`len(data) > 1024`). Malformed payloads or oversized strings skip processing immediately.
- **Connection Capacity:** Mitigates DoS via `ConnectionManager.max_connections`. Excess connections are safely dropped with HTTP Code `1013`.

## 5. Security Hardening Roadmap

To further elevate the security posture of the WebSocket and data model implementations, the following steps are recommended:

1. **Origin Scheme Verification:** Switch from naive string matching to explicit parsing (Scheme, Host, Port) using standard URL parsers to prevent bypasses like `https://allowed-origin.evil.com`.
2. **WebSocket Rate Limiting:** Enforce IP-based rate limiting on the `/ws` endpoint independently to prevent DoS via rapid connect-and-close cycles.
3. **Cryptographic Salt for Hashes:** If `Proxy.id` hashes are exposed externally, inject a server-side salt into the SHA-256 composite string to prevent offline dictionary attacks on embedded credentials (like `password`).
4. **Header Anomaly Detection:** Drop connections that omit critical standard browser headers (e.g., User-Agent) but include Origin, potentially flagging automated CSWSH probing tools.
