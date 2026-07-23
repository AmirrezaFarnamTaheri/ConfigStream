# Client Adapter Profiles Audit Report

## 1. Third-Party Client Adapter Architecture Flowchart

```ascii
                      +------------------+
                      | Proxy Models     |
                      | (Data Source)    |
                      +---------+--------+
                                |
                                v
                      +------------------+
                      |  native_configs  |
                      |  (Orchestrator)  |
                      +---------+--------+
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
+---------------+       +---------------+       +---------------+
| SurgeAdapter  |       | LoonAdapter   |       | QuantumultX   | ... Shadowrocket
+-------+-------+       +-------+-------+       +-------+-------+
        |                       |                       |
        |  Generates Proxy      |  Generates Proxy      |  Generates Proxy
        |  Strings (conf)       |  Strings (conf)       |  Strings (conf)
        |                       |                       |
        v                       v                       v
+---------------------------------------------------------------+
|                      Profile Wrappers                         |
|  (e.g., wrap_surge_or_loon_profile, wrap_quantumultx_profile) |
+-------------------------------+-------------------------------+
                                |
                                v
                        Client Profiles
                      (Surge, Loon, QX, SR)
```

## 2. Syntax & Parameter Mapping Compliance Matrix

| Protocol | Parameter     | Surge | Shadowrocket | QuantumultX | Loon | Notes / Audit Findings |
|----------|---------------|-------|--------------|-------------|------|------------------------|
| **SS**   | Method        | ✔     | ✔            | ✔           | ✔    | All adapters support SS adequately. |
|          | Password      | ✔     | ✔            | ✔           | ✔    | |
| **VMess**| UUID          | ✔     | ✔            | ✔           | ✔    | Surge/Loon uses `username=uuid`. QX uses `password=uuid`. SR uses `id=uuid`. |
|          | SNI           | ✔     | ✔            | ✔           | ✔    | QX/Loon parse correctly via `_extract_sni`. |
|          | WS Path       | ❌    | ✔            | ❌          | ❌   | **CRITICAL**: Missing in Surge, QX, Loon. |
|          | WS Headers    | ❌    | ❌           | ❌          | ❌   | Missing in all adapters except SR (handled partially). |
|          | Host / Obfs   | ❌    | ✔            | ❌          | ❌   | |
| **VLESS**| UUID          | ✔     | ✔            | ✔           | ❌   | Loon adapter lacks VLESS support entirely. |
|          | SNI           | ✔     | ✔            | ✔           | N/A  | |
|          | XTLS / Flow   | ❌    | ✔            | ❌          | N/A  | Flow is missing in Surge, QX. |
| **Trojan**| Password     | ✔     | ✔            | ✔           | ✔    | |
|          | SNI           | ✔     | ✔            | ✔           | ✔    | QX uses `tls-host`. |
|          | Path          | ❌    | ✔            | ❌          | ❌   | |
| **Hy2**  | Password      | ✔     | ✔            | ❌          | ❌   | QX and Loon lack Hysteria2 support. |
|          | SNI           | ✔     | ✔            | N/A         | N/A  | |

## 3. Special Protocol Support & Fallback Handling Audit Table

| Adapter      | WireGuard Support | Chains (Shielded/Revived) | VLESS / TUIC / Hy2 | Fallback Handling |
|--------------|-------------------|---------------------------|--------------------|-------------------|
| Surge        | Partial           | ✔ (Via native wrapper)    | ✔ VLESS/Hy2/TUIC   | Chains supported via `format_singbox_chain_for_surge`. |
| Shadowrocket | ✔                 | ✔ (Revived URIs extracted)| ✔ All modern       | Best protocol fallback support. Extracts URIs gracefully. |
| QuantumultX  | ❌                 | ❌                        | VLESS only         | No chain support. Lacks modern protocols (TUIC, Hy2). |
| Loon         | Partial           | ✔ (Via native wrapper)    | ❌                 | Chains supported via `format_singbox_chain_for_loon`. |

## 4. Output Matrix Contract Verification Summary

Upon auditing `docs/output_matrix.json`, it is evident that **none of the third-party client profiles (Surge, Loon, QuantumultX, Shadowrocket config files) are declared in the output matrix contract.**
- `native_configs.py` implements generation wrappers for these profiles (`wrap_surge_or_loon_profile`, etc.).
- However, `docs/output_matrix.json` only tracks `singbox.json`, `clash.yaml`, `base64.txt`, `proxies.txt`, and side products.
- **Verification Failure**: The generated artifacts are orphaned. They must be added to `output_matrix.json` to ensure they undergo pipeline integrity checks.
- **Base64 Header & User-Agent Handling**: The base64 generation (`generators/base64.py`) lacks custom subscription headers (e.g., `Profile-Title`, `Profile-Update-Interval`). User-Agent handling is present in `fetcher.py` and `singbox_utils.py` but is missing for standard HTTP transport parameter generation in adapters.

## 5. Code Hardening Patches

Below are suggested code hardening patches to rectify parameter truncation vulnerabilities in the adapters.

### Patch 1: Add WS Path and Host to Surge Adapter
```python
# In src/configstream/adapters/surge.py
def _format_proxy(self, p: Proxy) -> str:
    # ... existing code ...
    if p.protocol == "vmess":
        uuid = p.uuid
        sni = _extract_sni(p.details)
        sni_part = f", sni={sni}" if sni else ""
        ws_path = p.details.get("ws_path") or p.details.get("path", "")
        ws_part = f", ws=true, ws-path={ws_path}" if ws_path else ""
        host = p.details.get("host") or p.details.get("http_host", "")
        host_part = f", ws-headers=Host:{host}" if host else ""
        return f"{name} = vmess, {p.address}, {p.port}, username={uuid}{sni_part}{ws_part}{host_part}"
```

**Note:** `ws_path`, `host`, `sni`, and credentials must be escaped/quoted before adapter text concatenation, rejecting control characters.

### Patch 2: Add Path and Host to Quantumult X Adapter
```python
# In src/configstream/adapters/quantumult.py
def _format_proxy(self, p: Proxy) -> str:
    # ... existing code ...
    if p.protocol == "vmess":
        uuid = p.uuid
        method = p.details.get("method", "chacha20-poly1305")
        sni = _extract_sni(p.details)
        sni_part = f", tls-host={sni}" if sni else ""
        ws_path = p.details.get("ws_path") or p.details.get("path", "")
        obfs_part = f", obfs=ws, obfs-uri={ws_path}" if ws_path else ""
        host = p.details.get("host") or p.details.get("http_host", "")
        host_part = f", obfs-host={host}" if host else ""
        return f"vmess={name}: {p.address}, {p.port}, method={method}, password={uuid}{sni_part}{obfs_part}{host_part}"
```

**Note:** `ws_path`, `host`, `sni`, and credentials must be escaped/quoted before adapter text concatenation, rejecting control characters.

### Patch 3: Register Output Matrix Definitions
Add the following objects to `docs/output_matrix.json`:
```json
{"path": "surge.conf", "family": "surge", "category": "subscription", "format": "text", "required": true, "nonempty": true, "schema_validation": false, "degraded_valid": true, "notes": "Surge profile format."},
{"path": "quantumultx.conf", "family": "quantumultx", "category": "subscription", "format": "text", "required": true, "nonempty": true, "schema_validation": false, "degraded_valid": true, "notes": "QuantumultX profile format."},
{"path": "loon.conf", "family": "loon", "category": "subscription", "format": "text", "required": true, "nonempty": true, "schema_validation": false, "degraded_valid": true, "notes": "Loon profile format."},
{"path": "shadowrocket.conf", "family": "shadowrocket", "category": "subscription", "format": "text", "required": true, "nonempty": true, "schema_validation": false, "degraded_valid": true, "notes": "Shadowrocket profile format."}
```
