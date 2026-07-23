# DNS Scanner Tools & Sub-process Execution Audit

## 1. DNS Scanner Architecture & Sub-process Execution Flowchart

```text
+-------------------+       +-----------------------+       +------------------------+
|    User CLI /     |       |   Python / Bash       |       |  External Binaries     |
|    TUI Interface  | ----> |   Execution Engine    | ----> |  (vwarp, ping, dig,    |
+-------------------+       +-----------------------+       |   slipstream-client)   |
        |                           |                       +------------------------+
        |                           |                                 |
        |   +-------------------+   |                                 |
        +-> | Async IO / Thread | <-+   (asyncio / concurrent.futures)|
            | Pool Management   |                                     |
            +-------------------+                                     |
                    |                                                 |
            +-------------------+                                     |
            | Socket Management | <-----------------------------------+
            | (TCP/UDP/TLS/HTTP)|
            +-------------------+
```

## 2. Shell Injection & Active Scanning Policy Compliance Matrix

| Component | Sub-process Engine | Shell Injection Risk | `ALLOW_ACTIVE_SCANNING` Compliance | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `dnsscanner_tui.py` | `asyncio.create_subprocess_exec` | Low (No `shell=True`, separate args) | Non-compliant (Missing) | Uses explicit argument lists, escaping input correctly. Unconditionally scans domains/ports. |
| `lab-scanner.py` | `subprocess.run` | Low (No `shell=True`, separate args) | Non-compliant (Missing) | Uses `ping` and `vwarp` without `shell=True`. Scans CF subnets unconditionally. |
| `dnsScanner.sh` | `parallel`, `timeout`, `dig` | Medium (Shell environment) | Non-compliant (Missing) | Subnet expansion passes inputs via variables. Parallel securely handles the generated IPs. Unconditionally scans subnets. |

*Note: All tools currently lack an `ALLOW_ACTIVE_SCANNING=false` safeguard and initiate connections/scans by default or via unconstrained command line switches.*

## 3. DNS Timeout & Socket Resource Management Audit Table

| Module/Function | Timeout Setting | Resource Management (Sockets/Files) | Concurrency / Bounds |
| :--- | :--- | :--- | :--- |
| `dnsscanner_tui.py:scan()` | 2.0s (DNS) / 15.0s (HTTP/SOCKS) | Uses `httpx.AsyncClient` keep-alives and `aiodns` handles sockets. File handles closed properly. | Bounded via `asyncio.Semaphore(100)` by default. |
| `lab-scanner.py:tcp_connect` | 3.0s - 5.0s | Socket explicitly created; uses `finally: s.close()`. | Multi-threading via `ThreadPoolExecutor(max_workers=30)`. |
| `lab-scanner.py:udp_probe` | 3.0s | Socket explicitly created; uses `finally: s.close()`. | Managed by calling ThreadPool pool. |
| `lab-scanner.py:dns_resolve` | 3.0s | Socket explicitly created; uses `finally: s.close()`. | Handled natively; UDP single-shot. |
| `dnsScanner.sh` | 1s (`timeout 1 dig`) | Depends on `dig` and OS socket closure. | Managed via GNU `parallel -j <threads>`. |

## 4. Terminal Output Sanitization & Credential Protection Assessment

- **`lab-scanner.py`**:
  - The script parses custom proxy URIs via `_parse_proxy_uri(uri: str)`.
  - It intentionally (or unintentionally) discards everything before the `@` symbol in SOCKS/HTTP URLs (`rest[at_idx + 1 :] if at_idx >= 0 else rest`).
  - Thus, `user:pass` authentication details are completely stripped before the URL is rebuilt and logged.
  - **Verdict**: Credentials are inadvertently protected from terminal output, but this breaks authenticated proxy functionality. Overall, no sensitive secrets are leaked to stdout.
- **`dnsscanner_tui.py`**:
  - TUI logs the domain, DNS IP, and proxy URLs used for Slipstream. No sensitive credential logging is present since it doesn't take proxy auth input.
  - **Verdict**: Output is sanitized.
- **`dnsScanner.sh`**:
  - Outputs responding IPs securely. No credentials exist in scope.

## 5. Hardening & Code Optimization Patches

### A. Implement `ALLOW_ACTIVE_SCANNING` Safeguard
Enforce a zero active scanning default by wrapping all subnet/port scanning logic in a check against environment variables.
```python
# lab-scanner.py & dnsscanner_tui.py
import os
if os.environ.get("ALLOW_ACTIVE_SCANNING", "false").lower() != "true":
    print("Error: Active scanning is disabled by default. Set ALLOW_ACTIVE_SCANNING=true to proceed.")
    sys.exit(1)
```

### B. Fix Proxy Authentication Parsing in `lab-scanner.py`
Currently, `_parse_proxy_uri` strips `user:pass` making it safe but broken. Needs to retain credentials securely and mask them ONLY when logging.
```python
# Instead of dropping credentials completely:
def safe_log_proxy(proxy_url):
    import urllib.parse
    parsed = urllib.parse.urlparse(proxy_url)
    if parsed.password:
        return proxy_url.replace(f"{parsed.username}:{parsed.password}", "***:***")
    return proxy_url
```

### C. Restrict Default Concurrency
`dnsscanner_tui.py` defaults to a concurrency of `100`, which might trigger local firewall rate-limiting or socket starvation on lower-end systems. Recommend defaulting to `30-50`.

### D. Shell Hardening
In `dnsScanner.sh`, ensure `gtimeout`/`timeout` and `dig` commands are executed with full paths or ensure `PATH` is sanitized to prevent binary hijacking.
