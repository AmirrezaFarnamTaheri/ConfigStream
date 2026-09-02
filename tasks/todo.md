# Tasks: ConfigStream Target-State Roadmap Delivery

## Phase 1: Release Pipeline & Deployment Qualification (P0 Blockers)
- [x] **Task 1: Close Deploy Runner Validator Runtime Dependencies**
  - [x] Add `pydantic>=2.0.0` and `pydantic-settings>=2.0.0` to `.github/workflows/deploy-pages.yml:91`
  - [x] Verify `validate_frontend_placeholders.py --strict` executes cleanly in isolated runner environment
  - [x] Confirm `DEPLOY_READY=true` is set on valid candidate artifacts
- [x] **Task 2: Harden Cross-Language Ed25519 Byte Envelope & Negative Vectors**
  - [x] Verify UTF-8 canonical byte serialization parity between `signer.py` and `verifier.js`
  - [x] Add positive and negative test vectors in `tests/unit/test_signer.py`
  - [x] Verify rejection of tampered timestamps and public key mismatches
- [x] **Task 3: Enforce Trust Bootstrap Sequence Across All Frontend Surfaces**
  - [x] Standardize script loading order (`runtime-config.js` -> `constants.js` -> `verifier.js` -> `artifact-guard.js`) on all 9 `.html` files
  - [x] Add automated regression test in `tests/unit/test_frontend_structure.py` and `tests/unit/test_frontend_bootstrap.py`
  - [x] Verify fail-closed behavior before trust bootstrapping completes

### Checkpoint: Foundation & Publication Gate
- [x] All Phase 1 tests pass (`pytest tests/unit/test_signer.py tests/unit/test_signer_canonical.py tests/unit/test_frontend_bootstrap.py`)
- [x] Deploy runner validation environment verified

---

## Phase 2: Frontend Trust States, Design Tokens & Accessibility (P1)
- [x] **Task 4: Implement 5-State Trust UI Contract in Core Controllers**
  - [x] Implement *Loading, Fresh, Stale, Invalid, Empty/Error* states in `main.js` and `proxies.js`
  - [x] Add persistent metadata-derived freshness banner (no visitor clock spoofing)
  - [x] Add fail-closed modal for invalid signatures with actionable retry triggers
- [x] **Task 5: Consolidate Design Tokens, Fix Sticky Header Occlusion & Focus Visible**
  - [x] Implement `--bg-base`, `--bg-surface`, `--bg-glass`, `--accent-cobalt`, `--accent-cyan` in `style.css`
  - [x] Add `scroll-margin-top: 80px` to all anchor sections (`#faq`, `#quick-search`, etc.)
  - [x] Add `:focus-visible { outline: 2px solid #06b6d4; outline-offset: 2px; }`
  - [x] Support `@media (prefers-reduced-motion: reduce)`
- [x] **Task 6: Enforce Tabular Numerics & WCAG 2.2 AA Touch Targets**
  - [x] Apply `font-variant-numeric: tabular-nums` to latencies, ports, IPs, and telemetry counters
  - [x] Enforce $\ge 44\times44\text{px}$ touch targets on mobile / $\ge 24\times24\text{px}$ on desktop
  - [x] Replace structural emojis with accessible SVG icons (Lucide / Simple Icons)

### Checkpoint: Frontend Trust & Visual Baseline
- [x] 5-state trust contract verified via mock fixtures
- [x] Anchor links scroll safely beneath sticky header at 375px, 768px, 1024px, and 1440px
- [x] WCAG 2.2 AA focus rings and touch targets verified

---

## Phase 3: Live Verification & Data Plane Optimization (P1 / P2)
- [x] **Task 7: Harden Live Candidate Identity Gate in Deployment Verifier**
  - [x] Enhance `scripts/verify_pages_deployment.py` to compare live commit SHA, run ID, and manifest digest
  - [x] Add negative regression test in `tests/unit/test_verify_pages_deployment.py`
- [x] **Task 8: Optimize Go Scanner UDP Timer Allocations & Memory Churn**
  - [x] Replace `time.After()` in packet receive select loop with reusable `time.NewTimer` in `scanner.go`
  - [x] Verify zero heap allocations per packet in benchmarks (`go test -bench=. -benchmem`)
  - [x] Maintain `defer recover()` guards and single-socket UDP multiplexing
- [x] **Task 9: Remediate Broad Exceptions in Python Parsers & Adapters**
  - [x] Refactor generic `except Exception:` blocks across `src/configstream/parsers/` and `adapters/`
  - [x] Catch explicit `(ValidationError, json.JSONDecodeError, TimeoutError, ValueError)`
  - [x] Run `pytest tests/unit/test_parser_exceptions.py tests/unit/test_parsers.py`

### Checkpoint: Backend & Verifier Hardening
- [x] `verify_pages_deployment.py` rejects stale live artifacts
- [x] Go scanner benchmarks confirm zero timer channel churn
- [x] Python parser suite passes with explicit exceptions

---

## Phase 4: WebGL Performance, Throttling & Progressive Enhancements (P3)
- [x] **Task 10: Globe.gl DPR Clamping, Offscreen Throttling & Context Recovery**
  - [x] Clamp pixel ratio to $\le 1.5$ in `frontend/assets/js/analytics.js`
  - [x] Attach `IntersectionObserver` to pause RAF when globe is offscreen
  - [x] Add `webglcontextlost` and `webglcontextrestored` event handlers
  - [x] Add teardown hook `window._disposeGlobe` and `.is-offscreen` CSS animation pause rules
- [x] **Task 11: Procedural 3D Polyhedral Hero Node with Reduced Motion**
  - [x] Implement Three.js procedural node on `index.html` with physical shader and wireframe cage
  - [x] Gate animation on `prefers-reduced-motion: reduce`
  - [x] Add clean disposal hook on route changes
- [x] **Task 12: Master Readiness Ledger & Documentation Synchronization**
  - [x] Update `docs/readiness.json` with latest test evidence and coverage
  - [x] Regenerate `STATUS.md`
  - [x] Update `docs/wiki/project/12-master-audit.md` closed milestones

### Checkpoint: Complete Delivery
- [x] Full Python roadmap and core test suite passes (`pytest`)
- [x] Go scanner and uTLS test suites pass
- [x] Sealed artifact and placeholder validation passes (`python scripts/validate_frontend_placeholders.py frontend`)
- [x] Readiness ledger reflects verified target state (`scripts/validate_status.py`)
