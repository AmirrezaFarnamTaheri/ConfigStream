# Cloudflare Edge Workers & DoH Proxy Security Audit

## 1. Edge Workers Architecture & Traffic Flow Diagram

```text
       +-------------+
       |   Client    | (Browser, DoH Client, V2Ray)
       +------+------+
              |
              | HTTPS (DoH / WebSocket)
              v
+-------------+-------------+
|    Cloudflare Edge        |
|  (subscription_worker.js) |
|      (doh_proxy.js)       |
|      (doh_path.js)        |
|      (simple_doh.js)      |
+-------------+-------------+
              |
       +------+-----------------------------+-----------------+
       |                                    |                 |
       v                                    v                 v
+-------------+                       +-----------+     +-----------+
| Upstream DoH|                       | Decoy     |     | Subs      |
|  Providers  |                       | Endpoints |     | Endpoints |
+-------------+                       +-----------+     +-----------+
(1.1.1.1, Google)                      (Anti-Censorship)
```

## 2. DoH Security & Header Sanitization Verification Table

| Component | Check Item | Status | Notes |
| :--- | :--- | :--- | :--- |
| **All Workers** | `Server` Header | **Warning** | Relies on default Cloudflare `Server: cloudflare`. No explicit sanitization or removal of upstream Server headers, which could leak upstream identities. |
| **All Workers** | `X-Powered-By` Header | **Pass** | Not present or injected in the scripts. |
| **doh_path.js** | Upstream Validation | **Pass** | Uses hardcoded provider arrays and strict `new URL()` validation. Limits DNS payload sizes (`MAX_DNS_REQUEST_SIZE = 512`, `MAX_DNS_RESPONSE_SIZE = 4096`). |
| **subscription_worker** | Token Sanitization | **Pass** | Uses V4 UUID Regex (`isValidUUID`) to sanitize user identifiers before processing. Prevents injection. |

## 3. CORS & Subdomain Origin Security Assessment

- **Policy Found**: All evaluated scripts (`doh_proxy.js`, `simple_doh.js`, `doh_path.js`) explicitly define `Access-Control-Allow-Origin: *`.
- **Security Impact (DoH)**: **Low Risk**. For DoH endpoints, wildcard CORS is an intentional requirement to allow web applications to resolve DNS directly from the browser regardless of their origin.
- **Security Impact (Subscription)**: **Moderate Risk**. If `subscription_worker.js` handles sensitive configuration payloads through browser-based interfaces, `*` CORS may expose configurations to malicious websites. It is recommended to restrict CORS strictly to trusted frontend domains or require authorization headers that mitigate CSRF.

## 4. Cloudflare Workers Resource Limit & Timeout Audit

- **Timeouts & CPU Limits**: `doh_path.js` and `doh_proxy.js` implement an `AbortController`-backed `fetchWithTimeout` function. The max timeout is bounded safely at 14,000ms (`REQUEST_TIMEOUT_MAX`). This is well below the Cloudflare free tier limit of 30s wall-clock time, effectively preventing Worker abrupt terminations.
- **Circuit Breakers**: `doh_path.js` implements a circuit breaker (timeout: `90000ms`) preventing excessive upstream failures from exhausting CPU/memory loops.
- **Memory Footprint**: Memory usage is kept in check by bounding byte buffer arrays (`byteLength` validations) preventing OOM (Out Of Memory) limits exceeding the 128MB ceiling.

## 5. Hardening & Security Recommendations

1. **Header Sanitization Improvements**: Strip out potentially sensitive upstream headers (e.g., `Server`, `Via`, `X-Powered-By`) before relaying the `Response` back to the client in `simple_doh.js` and `doh_proxy.js`.
2. **Strict CORS on Subscription Worker**: Restrict `Access-Control-Allow-Origin` on `subscription_worker.js` to specific trusted subdomains instead of `*` if it's interacted with via browsers.
3. **Upstream Response Validation**: Ensure that DoH proxy responses strictly validate `Content-Type: application/dns-message` to prevent malicious upstreams from injecting HTML payloads into the browser.
4. **Rate Limiting Enforcement**: Cloudflare Free tier workers share compute limits; abuse of the DoH proxy could exhaust quotas. Enforce robust IP-based rate limiting using Cloudflare KV or Durable Objects.
