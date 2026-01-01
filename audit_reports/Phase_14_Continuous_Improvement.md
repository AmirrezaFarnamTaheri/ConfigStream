# Phase 14: Continuous Improvement & Final Polish - Analysis Report

## 14. Overview
This phase audits tools for ongoing quality assurance.

## 14.1. Profiling
*   `scripts/profile_performance.py` exists.
*   **Recommendation**: Ensure it uses `yappi` or `cProfile` and can handle async code.

## 14.2. Regression Testing & Coverage
*   **Unit Tests**:
    *   `tests/unit/test_hedged_requests.py`: Mocks `AsyncMock` correctly. Covers race conditions.
*   **E2E Tests**:
    *   `tests/e2e/test_pipeline_real.py`: Runs full pipeline with `dry_run=True`.
    *   **Value**: This is a critical smoke test. It verifies the pipeline *wiring* without needing network.
    *   **Mocking**: Mocks `DEFAULT_BLOCKLIST.update` and `generate_pipeline_outputs`. This makes it fast and stable.
*   **Fixtures**: `tests/conftest.py` (implied) likely sets up async loop scope.

## 14.3. Master Roadmap
This report serves as the consolidation point for all improvement initiatives.

### High Priority
1.  **Architecture**: Split `requirements.txt` into dev/prod. Secure Vwarp download checksum. (Phase 1)
2.  **Pipeline**: Fix blocking I/O in `output_handler.py`. Fix race condition in `PipelineStats`. Make producer throttling dynamic. (Phase 2)
3.  **Parsing**: Enforce `MAX_CONFIG_LINE_LENGTH` in all parsers. (Phase 3)
4.  **Testing**: Fix race condition in `GoBatchTester.test_custom_configs`. (Phase 4)
5.  **Intelligence**: Prevent infinite recursion in Proxy Washer. (Phase 5)
6.  **Security**: Apply log sanitization to file handlers. (Phase 6)
7.  **Frontend**: Optimize `stego.js` memory usage. (Phase 7)
8.  **Edge Cases**: Fix unsafe `age=0` default in `freshness.py`. (Phase 15)
9.  **Tools**: Clean up dead code (`etag_cache.py`, `metrics.py`). (Phase 12, 10)
10. **Security**: Implement SHA256 verification for FFI binary in `ss_ffi.py`. (Phase 6)
11. **Testing**: Mitigate OOM risk in Go Scanner by capping CIDR range or using iterators. (Phase 4)

### Medium Priority
1.  **Docs**: Document DNS Caching limitation (HTTP-only). (Phase 15)
2.  **Transport**: Decouple `stego.py` clearly or integrate via flag. (Phase 11)
3.  **Tools**: Hardcoded WARP IPs in validator. (Phase 21)
4.  **History**: Stream large history exports. (Phase 12)
5.  **Frontend**: Tighten CSP in `index.html` (remove unsafe-inline). (Phase 7)
6.  **Scripts**: Atomic write fix for `clean_security_issues.py`. (Phase 9)
7.  **Frontend**: Move `calculateSimilarity` (fuzzy search) to Web Worker for large datasets. (Phase 7)

## 14.4. Linting
*   `flake8`, `black`, `mypy` are configured.
*   **Action**: Enforce them in CI (Phase 1).

## Recommendations
1.  **Async Profiling**: If `profile_performance.py` doesn't use `yappi`, update it. `cProfile` is bad for asyncio (profiles the loop, not the tasks).
2.  **Test Gaps**: Add a test for `GoBatchTester` that mocks the subprocess stdio to verify JSON parsing robustness without running the binary.
