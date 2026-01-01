# Phase 2: Core Pipeline Orchestration - Tracking

## Status: In Progress

### Tasks
- [x] **Concurrency**: Fix `PipelineStats` concurrency by adding defensive copy in `to_dict`. (Fixed in Step 2.3)
- [ ] **Blocking I/O**: Identify and fix any remaining blocking calls (e.g. `shutil`).
- [ ] **Producer Throttling**: Make producer semaphore dynamic.

## Verification
- `PipelineStats`: Validated via file read.
