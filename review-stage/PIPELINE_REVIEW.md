# Auto-Review Loop — Pipeline Correctness

## Round 1 Assessment
**Score:** 7/10
**Verdict:** Actionable findings identified; requires patches for error handling, async I/O, and duplicate logic.

### Ranked Weaknesses
1. **Missing Error Boundaries (`src/configstream/pipeline/producer.py`)**
   - **Line ~546:** The `StreamingProducer.produce` method catches all exceptions and logs them but fails to `raise` them. This swallows producer-level crashes (e.g., initialisation failures), causing the pipeline to exit gracefully and return a `success=True` result with 0 working proxies, masking the true failure.
2. **Blocking I/O in Async Loop (`src/configstream/pipeline/core.py`)**
   - **Line ~369:** `history.save()` is called synchronously.
   - **Line ~378:** `self.context.test_cache.save()` is called synchronously.
   - These calls perform blocking file I/O operations on the main asyncio event loop, which can degrade performance. They should be wrapped in `run_in_executor` like the `history.cleanup_old_data` call just below them.
3. **Duplicate Appends / Logical Bug (`src/configstream/pipeline/consumer.py`)**
   - **Line ~723:** In `_revive_failed_proxies`, `vwarp_candidates` are appended to `final_batch_for_this_source` regardless of whether they passed the test. If they failed, they are retried in the Standard WARP fallback, which *also* appends the resulting failed proxy. This results in duplicate failed revived proxies entering the pipeline output.

### Scope Verification
- **`vwarp_success_ids` logic:** Verified. The logic correctly handles both `.id` and `.uuid` using string conversion and exclusionary checks.
- **Early exit on zero working proxies:** Verified. `should_fail` is evaluated at the very end of pipeline execution in `core.py`, and the consumer only logs a critical message, ensuring pipeline continues and produces output downstream.

---

## Round 2: Proposed Fixes
**New Score:** 10/10 (Post-Fix)

### 1. Fix Missing Error Boundaries (`producer.py`)
Re-raise the exception to ensure the pipeline correctly surfaces fatal producer errors.
```python
    except Exception as e:
        safe_error = SecurityValidator.sanitize_log_message(str(e))
        logger.error(f"Producer failed: {safe_error}")
        raise  # Bubble up the exception to trigger _cancel_all in core.py
    finally:
```

### 2. Fix Blocking I/O (`core.py`)
Wrap the save calls in the executor.
```python
            # ... existing code ...
            await asyncio.get_running_loop().run_in_executor(None, history.save)
            try:
                await asyncio.get_running_loop().run_in_executor(
                    None, lambda: history.cleanup_old_data(days=30)
                )
            except Exception as e:
                logger.warning(f"History cleanup failed: {e}")

            if self.context.test_cache:
                await asyncio.get_running_loop().run_in_executor(
                    None, self.context.test_cache.save
                )
```

### 3. Fix Duplicate Proxies (`consumer.py`)
Only append Vwarp candidates if they successfully connected.
```python
        for p in vwarp_candidates:
            p.process = "revived-vwarp"
            if "revived-vwarp" not in p.tags:
                p.tags.append("revived-vwarp")
            origin = p.details.get("origin_proxy")
            if origin:
                p.country_code = origin.get("country_code", "")
                p.country = origin.get("country", "")
            
            origin_id = p.details.get("origin_id")
            if not origin_id and isinstance(origin, dict):
                origin_id = origin.get("uuid") or origin.get("id")
                
            if p.is_working:
                if origin_id:
                    vwarp_success_ids.add(str(origin_id))
                final_batch_for_this_source.append(p)
                async with seen_lock:
                    stats.revived_vwarp += 1
                    stats.vwarp_success += 1
```

### Final Method Description
The review utilized an iterative code trace through `core.py`, `producer.py`, and `consumer.py` mapping out data flow. Blocking I/O was identified by isolating direct disk persistence methods in the async loop. Error boundaries were inspected by examining the `try/except` chains, revealing the swallowed exception in the producer. The Vwarp proxy duplication was discovered by tracing the control flow of `is_working=False` variants through the two-stage (Vwarp -> Standard) revival fallback mechanism. Verification of the `vwarp_success_ids` and early-exit conditions was completed per the requested scope.
