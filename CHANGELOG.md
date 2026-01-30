[Output for brevity]

**Quality Checks**
- All 733 unit tests passing
- All modified files pass mypy, black, and flake8

---

## [2.1.0] - 2025-01-07

### Extensive Backend Audit & Source Expansion (Batch 14 Redistribution)

**Major Enhancements**
- **Source Expansion**: Added ~100 new proxy sources (URLs/APIs) and redistributed them evenly into 14 batches (800+ total unique sources).
- **Dynamic Resharding**: Created and executed `scripts/redistribute_sources.py` to:
    - Collect all sources from existing batch files (and new sources).
    - Deduplicate and balance them evenly into 14 optimized batches (`batch_1` to `batch_14`).
- **Fetcher Robustness**:
    - Fixed handling of "200 OK" empty responses (now logged clearly as "Empty content" instead of failure).
    - Patched `MAX_RESPONSE_SIZE` to respect `AppSettings` (200MB) instead of hardcoded 10MB limit.
    - Added sanitization for malformed GitHub raw URLs.
- **Parsing Improvements**:
    - Updated `extraction.py` to support JSON arrays (e.g., `["vmess://..."]`) and YAML files detected by extension.
    - **Critical SOCKS Fix**: Fixed a bug where plain `IP:port` lists from SOCKS sources were being tested as HTTP. The parser now infers `socks5://` or `socks4://` scheme from the source filename context.
- **Scoring & Ranking**:
    - Integrated `calculate_health_score` (reliability + latency + uptime) into `consolidation.py` and `sorter.py`.
    - Updated `rank_and_rename_proxies` to include country flags in remarks (e.g., `VMESS-1 [🇺🇸]`).
    - Updated stale proxy penalty calculation (2.0x latency multiplier).
- **Concurrency & Thread Safety**:
    - Added explicit async locks in `consumer.py` to ensure thread-safe updates to `PipelineStats` drop reasons.
    - Updated `output_handler.py` to reuse `Washer` instances, preventing redundant initialization logs.
- **Intelligence**:
    - Updated `washer/core.py` to allow dynamic loading of WARP peer keys from `AppSettings`.

**Test Suite & Quality**
- **Verification**: Ran full `pytest` suite (700 tests passed).
- **Code Quality**: Formatted codebase with `black`, linted with `flake8`, and type-checked with `mypy`.
- **Environment**: Fixed dependency issues (`aiofiles`, `fastapi`, `cryptography`) in the test environment.

---

## [2.0.9] - 2025-12-22
...
