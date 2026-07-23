# Lab Chain Tester Security & WARP Chain Audit

## 1. Lab Chain Tester Flowchart

```ascii
              [ API / Client Request ]
                         |
                POST /api/lab/test-chain
            (JSON Config with Chained Outbounds)
                         |
               [ lab_chain_tester.py ]
                         |
                _ensure_config_ready()
           (Injects inbounds, route, logs)
                         |
   [!] VULNERABILITY: No Outbound Address Sanitization [!]
                         |
               [ SecureConfigContext ]
              (Writes JSON to temp file)
                         |
                  [ singbox2proxy ]
       (Spawns sing-box instance with chained config)
                         |
            aiohttp session via ProxyConnector
                         |
    +--------------------+---------------------+
    |                    |                     |
 GET test_url         GET ipify_url       Cleanup/Stop
 (15s total)           (5s total)           (5s total)
    |                    |                     |
    +--------------------+---------------------+
                         |
                Return Latency & Exit IP
```

## 2. Multi-Hop Outbound & WARP Layer Audit Table

| Component / Layer | Status | Risk Level | Findings & Notes |
| :--- | :--- | :--- | :--- |
| **Config Ingestion** | Blind Passthrough | **Critical** | The tester accepts arbitrary JSON dictionaries. It lacks structural validation of the `outbounds` array to ensure they represent a valid chain (e.g., `Relay -> WARP/Vwarp`) without malicious attributes. |
| **Outbound Routing** | Native sing-box | Low | Relies natively on `sing-box`'s routing/dialer system, correctly utilizing internal proxy chaining mechanics. |
| **SSRF Prevention** | Missing | **Critical** | `SecurityValidator.is_local_ip` is never invoked on the parsed outbounds. Attackers can specify internal targets (e.g., `127.0.0.1:6379`, AWS IMDS `169.254.169.254`) causing the testing server to proxy requests to internal resources. |
| **WARP/WireGuard** | Implicitly Supported | Medium | WARP endpoints require handshake resolution. Implicit support via sing-box is fine, but chain MTU or IPv6 endpoints aren't explicitly verified. |

## 3. Timeout & Latency Bounds Safety Assessment

**Current State:**
- Sing-box start timeout: `15.0s`
- Proxy test (`test_url`) total timeout: `15.0s`
- Exit IP fetch (`ipify_url`) timeout: `5.0s`
- Sing-box shutdown timeout: `5.0s`

**Assessment:**
- **Accumulated Latency Flakiness:** In multi-hop chains (e.g., VLESS Relay -> WARP), TCP handshake + TLS on hop 1, plus Wireguard initialization on hop 2, sequentially accumulate. A flat 15-second total timeout is often too aggressive for deep chains, resulting in false negatives.
- **Missing Hop-by-Hop Metrics:** Latency is measured end-to-end. There is no tracking of intermediate hop latency, making chain bottleneck diagnosis impossible.
- **Resource Exhaustion Risk:** Slowloris or tarpit proxies can occupy the executor up to the max timeout. A flat upper bound is safe for the host, but the distribution of timeouts could be optimized.

**Optimization:**
- Implement dynamic timeout scaling: `timeout = base_timeout + (hop_count * 5.0)`.
- Enforce an absolute ceiling (e.g., `30.0s`) to prevent worker starvation.

## 4. Security Sanitization Verification

**Strengths:**
- **Log Sanitization:** Exception messages gracefully pass through `SecurityValidator.sanitize_log_message()`, successfully masking embedded UUIDs, passwords, or IPs that might leak from native sing-box errors.
- **File Security:** `SecureConfigContext` correctly isolates the temporary configuration file from disk snooping or collisions.

**Weaknesses:**
- **Pre-execution Sanitization is absent.** The function relies on post-failure sanitization. The parameters *within* `config` are fully trusted.
- **Recommendation:** Implement a pre-execution outbound scanner that iterates through `config.get("outbounds", [])`, extracting any `server` fields and rejecting local, private, or suspicious IP ranges using `SecurityValidator.is_local_ip()`.

## 5. Code Hardening Patches

Apply the following patches to `src/configstream/testers/lab_chain_tester.py`:

### Patch 1: Implement Dynamic Timeout and SSRF Blocking

```python
# Add this near the imports
from ..security_validator import SecurityValidator

def _validate_and_sanitize_outbounds(config: Dict[str, Any]) -> None:
    """Pre-flight security check against SSRF and suspicious ports."""
    outbounds = config.get("outbounds", [])
    for outbound in outbounds:
        server = outbound.get("server")
        if server and SecurityValidator.is_local_ip(server):
            raise ValueError(f"Security violation: Local IP address blocked in outbound: {server}")
        # Optionally validate ports against SUSPICIOUS_PORTS

# In test_chain_config() definition, update the logic:
async def test_chain_config(
    config: Dict[str, Any],
    base_timeout: float = 15.0,
    test_url: str = "https://www.google.com/generate_204",
    ipify_url: str = "https://api.ipify.org?format=json",
) -> Dict[str, Any]:
    
    # ... availability checks ...
    
    try:
        ready_config = _ensure_config_ready(config)
        # Apply security validation
        _validate_and_sanitize_outbounds(ready_config)
        
        # Dynamic timeout adjustment based on chain depth
        outbound_count = len([ob for ob in ready_config.get("outbounds", []) if ob.get("type") != "direct"])
        dynamic_timeout = min(base_timeout + (outbound_count * 4.0), 30.0)
        
        config_content = json.dumps(ready_config)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    # ... remaining execution using dynamic_timeout instead of timeout ...
```
