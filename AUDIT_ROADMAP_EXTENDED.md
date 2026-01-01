# AUDIT_ROADMAP_EXTENDED.md

## 1. Overview
This expanded roadmap targets 100% codebase perfection, covering all languages (Python, Go, Rust, JS), workflows, and configurations. It is based on a deep inventory and best-practice research.

## 2. Core Backend & Pipeline

### 2.1. Concurrency Safety (`src/configstream/pipeline_core/consumer.py`)
- [ ] **Critical Fix**: `final_proxies.append(p)` and `stats.working += 1` are protected by `seen_lock`, but `stats.drop_reasons` updates inside the test loops might race if multiple consumers run (they do).
    - **Action**: Ensure ALL updates to shared `stats` object are under `async with seen_lock`.
- [ ] **Revival Logic**: The revival loop blindly attempts both Vwarp and Warp.
    - **Optimization**: If `vwarp_candidates` succeeded, should we skip `warp_candidates` for those same proxies? Currently it does both.
    - **Recursion**: Verify `p.protocol == "revived"` check prevents infinite loops (Checked: it relies on `failed_proxies` which comes from `native` tests, so depth is 1. Safe).

### 2.2. Fetcher Resilience (`src/configstream/fetcher_core/orchestrator.py`)
- [ ] **Optimistic Failure**: The fix `[FIX] "Optimistic Failure" Bug` handles empty content but retries it.
    - **Refinement**: If content is empty (0 bytes), it should probably check headers (`Content-Length`) to distinguish "empty file" from "network truncation".

## 3. Go Tester (`src/go/tester/main.go`)

### 3.1. JSON Decoding
- [ ] **Token Limit**: The code uses `json.NewDecoder` (Good).
- [ ] **Context Injection**: `setupSingbox` creates a `box` instance.
    - **Critical**: `box.New` initializes the global registry. If `sing-box` library relies on global state, parallel tests might interfere? (Research: `sing-box` v1.9+ moved to instance-based registry, so `box.New` is safe).

### 3.2. Networking
- [ ] **Port Binding**: `port := 10000 + getRandomInt(50000)`.
    - **Race**: Random ports can collide. `sing-box` will fail to bind. The retry loop handles this, but `net.Listen` check is removed (Good).
- [ ] **Transport**: `http.Transport` disables keep-alives. This is good for `localhost` ephemeral ports.

## 4. Rust Component (`src/rust/ss_checker`)

### 4.1. FFI Interface
- [ ] **Validation**: `verify_shadowsocks` in `lib.rs` performs string matching (`contains("method")`).
    - **Weakness**: It doesn't actually test the password/key validity or decode the payload. It just checks *structure*.
    - **Improvement**: Implement actual `shadowsocks-crypto` handshake or at least base64 decode the password to verify length.

## 5. Frontend & Steganography (`frontend/assets/js/stego.js`)

### 5.1. Key Management
- [ ] **Hardcoded Secret**: `const SECRET_KEY = "PLACEHOLDER_KEY_INJECTED_BY_CI";`.
    - **Verification**: Ensure the CI workflow (`.github/workflows/pipeline.yml`) actually performs this replacement (`sed` or similar). If not, stego fails silently in prod.

## 6. Parsing & Ingestion

### 6.1. Decoders (`src/configstream/parsers/decoders.py`)
- [ ] **Rate Limiting**: `RateLimitedLogger` is good.
- [ ] **Noise Check**: `invalid_count > threshold` (5%).
    - **Edge Case**: Some valid Base64 usages (e.g. VLESS URL query params) might have high density of "special" chars if double-encoded. Verify this threshold doesn't kill complex VLESS links.

### 6.2. Extraction (`src/configstream/parsers/extraction.py`)
- [ ] **Size Limit**: 50MB limit is hardcoded.
    - **Config**: Should be drawn from `constants.py` (`MAX_B64_INPUT_SIZE`).

## 7. Configuration & Constants

### 7.1. Private IPs
- [ ] **Missing Ranges**: `172.16.0.0/12` (Class B) is checked via regex `172\.(1[6-9]|2[0-9]|3[0-1])\.`. This is correct.
- [ ] **IPv6**: `fc00::/7` (ULA) checking: `r"^fc00:"`, `r"^fd00:"`. This covers it.

## 8. Action Plan (Execution Phase)

1.  **Backend**: Fix `stats` locking in `consumer.py`.
2.  **Go**: Add unit tests for `main.go` using Go's testing framework (currently missing/sparse).
3.  **Rust**: Enhance `verify_shadowsocks` to be robust or deprecate if unused (Python fallback exists).
4.  **Frontend**: Audit `.github/workflows` to ensure `SECRET_KEY` injection.
5.  **Docs**: Update `ARCHITECTURE.md` with the "Hybrid + Rust" discovery.
