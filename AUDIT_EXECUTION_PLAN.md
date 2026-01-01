# Audit Execution Plan (Phases 1-21)

This document consolidates all actionable tasks from the audit reports to ensure 100% coverage.

## Phase 1: Project Configuration & Architecture
- [ ] **Dependencies**: Split `requirements.txt` into `requirements.txt` (prod) and `requirements-dev.txt` (dev).
- [ ] **Dockerfile**: Add SHA256 checksum verification for `vwarp` binary.
- [ ] **Config**: Refactor `src/configstream/config.py` to use `pydantic-settings`.
- [ ] **Cleanup**: Remove unused `src/configstream/plugins/` directory.

## Phase 2: Core Pipeline Orchestration
- [ ] **Concurrency**: Replace blocking `subprocess.Popen.wait()` with `asyncio` for Vwarp.
- [ ] **IO**: Wrap blocking file operations (`shutil`) in `output_handler.py` with `run_in_executor`.
- [ ] **Stats**: Add locking to `PipelineStats` in `stats.py` to prevent race conditions.
- [ ] **Producer**: Make `asyncio.Semaphore(100)` in `producer.py` configurable/dynamic.

## Phase 3: Data Ingestion & Parsing
- [ ] **Fetcher**: Fix "Optimistic Failure" bug in `orchestrator.py` (fail on empty content).
- [ ] **Parsers**: Enforce `MAX_CONFIG_LINE_LENGTH` in all protocol parsers (`vless`, `vmess`, etc.).
- [ ] **VLESS**: Review and potentially relax UUID validation if too strict.
- [ ] **Extraction**: Ensure `extraction.py` uses `MAX_B64_INPUT_SIZE` constant.

## Phase 4: Testing Engine
- [ ] **Go Tester**: Add `io.LimitReader` to honeypot body reading (`main.go`).
- [ ] **Go Tester**: Enable socket reuse/pooling in `http.Client`.
- [ ] **Python Integration**: Fix race condition in `test_custom_configs` in `testers/go.py` (missing lock).

## Phase 5: Intelligence & Advanced Features
- [ ] **Washer**: Add check to prevent re-washing proxies that are already "revived" (infinite loop prevention).
- [ ] **Washer**: Implement persistence for discovered "Clean IPs" (disk cache).
- [ ] **Key Management**: Implement rotation/retiring of bad WARP keys.

## Phase 6: Cross-Cutting Concerns
- [ ] **Security**: Implement SHA256 checksum verification for `libss_checker.so` in `ss_ffi.py`.
- [ ] **Metrics**: Deprecate `metrics.py` if unused/redundant.

## Phase 7: Frontend & Output Artifacts
- [ ] **Stego**: Optimize `stego.js` memory usage (replace `slice` with `subarray`).
- [ ] **Security**: Refine CSP in `index.html` (remove `unsafe-inline` if feasible).

## Phase 9: Tools & Operational Scripts
- [ ] **Scripts**: Fix non-atomic file writes in `clean_security_issues.py`.
- [ ] **Workflows**: Verify `merge_batches.py` actually merges DBs, not just overwrites.

## Phase 12: Data Integrity & Artifacts
- [ ] **Cleanup**: Delete dead code `src/configstream/etag_cache.py`.
- [ ] **History**: Refactor `_load_all_history` in `tracker.py` to stream data (avoid OOM).
- [ ] **Rotation**: Implement logic to rotate `proxies.json` to `proxies.old.json`.

## Phase 15: Edge Case & Anomaly Handling
- [ ] **Freshness**: Change `freshness.py` to default to STALE (age=999999) on date parse error.
- [ ] **Docs**: Document that DNS Caching (`CachedDNS`) only works for HTTP, not HTTPS.

## Phase 17: Legal & Compliance
- [ ] **License**: Add SPDX headers to all source files.
- [ ] **Privacy**: Document that server access logs (uvicorn) are enabled by default.

## Phase 19: Configuration & Constants
- [ ] **Constants**: Add private IP ranges (Class B `172.16-31`, ULA `fc00::`) to `SUSPICIOUS_DOMAINS` or validator.

## Phase 21: Toolchain & Utilities
- [ ] **Warp Validator**: Refactor hardcoded IPs in `warp_validator.py` to use constants/config.
- [ ] **Warp Validator**: Fix/Verify Authentication logic (add token support).
