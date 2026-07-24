# Public Lists & Geo-Chaining Audit

## Architecture Diagram

```ascii
+-------------------+       +---------------------+       +-----------------------+
|  Proxy Sources    | ----> | Provenance Tracking | ----> | Serialization Engine  |
| (Raw Subscriptions)       | (Internal Details)  |       | (Sanitize _source)    |
+-------------------+       +---------------------+       +-----------------------+
                                                                 |
   +-------------------------------------------------------------+
   |
   v
+-------------------------+      +---------------------------+
| Geo-Chaining Engine     |      | Output Generator          |
| (Haversine & Centroids) |      | (public_lists.py)         |
| - Relay Selection       | ---> | - Country: {cc}.list.json |
| - Geo Distance Penalties|      | - Proto: {proto}.list.json|
+-------------------------+      +---------------------------+
```

## Provenance Key Sanitization & Serialization Verification

- **Internal Key Stripping**: `serialize_proxy()` in `src/configstream/serialize.py` successfully filters out internal properties from `proxy.details` by explicitly removing keys that start with `_` or `has_`. This prevents leakage of raw backend state like `_source`.
- **Source Sanitization**: The `_sanitize_source` function correctly parses the `raw_source` and extracts only the `netloc` (domain). If it fails to parse as a URL, it falls back to generating a 12-character SHA-256 hash. This guarantees the original full subscription tokens or paths are not exposed.
- **Top-Level Inclusion**: The sanitized source domain or hash is properly exposed at the top level of the JSON payload under `"source": _sanitize_source(raw_source)`.

## Haversine Formula & Country Centroid Precision Audit

- **Distance Fallback Reliability**: `chaining.py` correctly implements the Haversine formula as a fallback when `geopy` is absent. It features crucial domain-error prevention by clamping the `a` parameter (`min(1.0, max(0.0, a))`) before applying `math.asin()`, preventing math domain errors during edge case precision loss near antipodal points.
- **Centroid Coordinates**: The hardcoded `COUNTRIES` dictionary uses approximate geographic centers for over 80 key countries. These serve well for macro-level routing decisions but may lack precision for large countries (e.g., US, RU, CN) where picking a single center point might result in sub-optimal relay routing compared to city-level IP geolocation.

## ISO-3166 Country Code Mapping Completeness Matrix

- `frontend/assets/data/countries.json` holds a comprehensive mapping of English country names to standard ISO-3166 alpha-2 codes (e.g., `"Germany": "DE"`).
- The mapping is complete for the 80+ countries defined in the `chaining.py` centroid list, plus hundreds more. It accurately matches the standard 2-letter capitalization used across `public_lists.py` (which enforces uppercase `(p.country_code or "XX").upper()`).

## Code Hardening Recommendations

1. **City-Level Geolocation Support**: The current geo-chaining logic relies purely on country-level centroids. Incorporate MaxMind GeoLite2 or similar for city-level coordinates to improve latency estimations inside large landmasses like the US and China.
2. **Robust Type Enforcement in `_sanitize_source`**: If `raw_source` somehow turns out to be non-string (e.g., accidentally an int or dict), `urlparse` might raise a `TypeError` not caught by the broad `Exception` block, or `raw_source.encode("utf-8")` will fail. Preemptively cast to `str` or validate type.
3. **Optimize Haversine Iterations**: In `generate_smart_chains`, calculating `haversine` repeatedly across nested loops could be slow. Consider caching pairwise distances for known centroid combinations during initialization.
4. **Graceful Handle of `_process` Mutability**: Modifying `exit_out["_process"] = "chain"` in `create_chain` without deepcopying the underlying dictionary might inadvertently mutate global state if the inbound `exit_node` representations were cached. Ensure `to_singbox_outbound` generates a clean copy.
