# Phase 10: Refactoring & Cleanup Targets - Analysis Report

## 10. Overview
This phase identifies technical debt, code duplication, and opportunities for cleanup based on previous phases.

## 10.1. Split Brain (Python vs Go)
**Analysis**:
*   **Duplicate Logic**:
    *   **SingBox Config**: Both Python (`to_singbox_outbound`) and Go (internal library) likely generate configs. Go relies on Python to pass the config JSON, so Python is the source of truth for *generation*. This is GOOD (no split brain in generation).
    *   **Testing**: Both have testing logic. Go is "Batch Tester", Python is "Fallback".
    *   **Honeypot**: Go does it. Python `blocklist.py` has deprecated logic.
*   **Consolidation**:
    *   Move `is_suspicious_port` to Go if possible to avoid Python overhead, or keep it as a pre-filter.
    *   Deprecate Python Tester for complex protocols completely if `singbox2proxy` is optional and slow.

## 10.2. Code Duplication
*   **Parsers**: `vmess`, `vless`, `trojan` share URL parsing logic.
    *   Refactor into `src/configstream/parsers/utils.py` (already partially done).
*   **Warp Logic**:
    *   `bot_cli.py` calls `tools.warp`.
    *   `washer/core.py` calls `tools.vwarp` (different module?).
    *   **Check**: Is `tools.warp` (Python API) duplicate of `tools.vwarp` (Binary wrapper)?
    *   **Action**: Unify or clearly distinguish (e.g. `warp_api.py` vs `warp_cli.py`).

## 10.3. Type Hints
*   **Status**: Most code has type hints.
*   **Strictness**: `mypy.ini` exists.
*   **Action**: Enforce `strict=True` in critical modules (`pipeline.py`, `parsers/`).

## 10.4. Utility Audit
*   `src/configstream/utils/`:
    *   `AtomicFileWriter`: Keep.
    *   `bool_parser.py`: Use `pydantic` or `distutils.util.strtobool` (deprecated) / explicit map.

## Recommendations
1.  **Deprecate Legacy**: Remove `is_honeypot` in `blocklist.py`.
2.  **Unify Warp**: Clarify `tools.warp` vs `tools.vwarp`.
3.  **Strict Typing**: Enable strict mypy for `src/configstream/pipeline_core`.
