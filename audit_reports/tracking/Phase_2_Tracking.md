# Phase 2: Core Pipeline Orchestration - Tracking

## Status: Complete

### Tasks
- [x] **Concurrency**: Fix `PipelineStats` concurrency by adding defensive copy in `to_dict`.
- [x] **Blocking I/O**: Identify and fix any remaining blocking calls in `output_handler.py`.
- [x] **Producer Throttling**: Make producer semaphore dynamic via `PRODUCER_MAX_CONCURRENCY`.

## Verification
- `PipelineStats`: Validated.
- `output_handler.py`: Validated.
- `producer.py`: Validated.
