# Phase 0: Immediate Critical Fixes - Tracking

## Status: In Progress

### Tasks
- [x] **Security**: Fix `pip_audit_wrapper.py` to use `check=True`. (Fixed in Step 2.1)
- [x] **Testing**: Fix `test_hedged_requests.py` to verify task cancellation. (Fixed in Step 2.2)
- [ ] **Logging**: Verify `logging_config.py` applies filters correctly. (Verified as correct in analysis, no code change needed unless regression found).

## Verification
- `pip_audit_wrapper.py`: Validated via file read.
- `test_hedged_requests.py`: Validated via `pytest`.
