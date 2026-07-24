# Split Generator & Sing-box Outbound Caching Efficiency Audit

## Outbound Cache Memory & CPU Flowchart
```ascii
[Proxies (10,000+)]
       |
       v
[Base Cache Generation]
   - calls to_singbox_outbound() ONCE per proxy
   - stores Dict[str, Any] in `_base_outbound_cache`
       |
       +-----------------------------------------+
       |                                         |
       v                                         v
[Sniper Profile (Evasion)]               [Tank Profile (Clean)]
   - copy.deepcopy(base_ob)                 - copy.deepcopy(base_ob)
   - Mutates dict with evasion              - Retains clean dict properties
       |                                         |
       v                                         v
[singbox.json (Sniper)]                  [singbox-vpn.json (Tank)]
```

## Deepcopy Overhead & Performance Benchmark Analysis
- **Current State**: `copy.deepcopy()` is utilized in `src/configstream/generators/split.py` to duplicate the base outbounds for both the Sniper and Tank profiles. 
- **Overhead Impact**: Python's `deepcopy` is recursively slow. For 10,000+ proxies, generating two copies results in creating over 30,000 outbound dictionaries in memory (Base + Sniper + Tank). This causes significant CPU blocking time during config generation and spikes in RAM usage.
- **Redundancy**: The Tank profile generally requires no mutations to deeply nested structures (only top-level `tag` alterations). Using `deepcopy` for Tank is an unnecessary performance penalty.

## Percent-Encoding Path Sanitization Audit Table
Sanitization in `src/configstream/converters/singbox_utils.py` uses `_BAD_PERCENT_RE`.

| Protocol/Transport | Field Affected | Regex Engine | Assessment |
| :--- | :--- | :--- | :--- |
| `ws` | `transport["path"]` | `%(?![0-9A-Fa-f]{2})` | **PASS**. Safely encodes orphaned `%` to `%25` without corrupting valid hex encodings like `%20` or `%2F`. |
| `http` / `h2` | `transport["path"]` | `%(?![0-9A-Fa-f]{2})` | **PASS**. Proper normalization prevents Sing-box unmarshal crashes. |
| `httpupgrade` | `transport["path"]` | `%(?![0-9A-Fa-f]{2})` | **PASS**. Integrated successfully per Sing-box schema. |

## Profile Output Generation Integrity Checklist
- [x] **Sing-box Base Cache**: `to_singbox_outbound()` safely strips unsupported metadata and is accurately cached to avoid duplicate computations.
- [x] **Clash Output**: Clash configurations avoid the `_base_outbound_cache` and utilize `generate_clash_config()` directly, preserving protocol structure integrity.
- [x] **Third-Party Adapters (Surge/Shadowrocket/QuantumultX)**: `native_configs.py` safely clones proxies using Pydantic's `model_copy(deep=True)` to rebuild configs with safe DNS routing without mutating the original proxy list.
- [x] **Tag Collisions Avoidance**: `split.py` properly suffixes duplicate tags ensuring `urltest` and `selector` arrays don't break.

## Performance & Memory Optimization Recommendations
1. **Targeted Dict Cloning**: Replace `copy.deepcopy()` with a fast custom structural cloner (e.g., shallow copy the base dict, and only explicitly copy the `tls` and `transport` sub-dictionaries).
2. **Downgrade Tank Copy**: Change the Tank profile to use a simple shallow copy (`base_ob.copy()`). Since Tank doesn't alter the `transport` or `tls` payload for evasion, shallow copying is perfectly safe and saves ~33% memory footprint instantly.
3. **Pydantic Model Clones in Adapters**: `model_copy(deep=True)` in `native_configs.py` is safe but slow for huge lists. If scaling beyond 10,000 items, consider caching the DNS hostmaps and passing them to the adapters directly instead of fully duplicating the Proxy objects.
