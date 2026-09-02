# Implementation Plan: ConfigStream Target-State Roadmap Delivery

## Overview
Decompose and execute the target-state architectural specifications, release blockers, and technical debt remediations identified in `docs/wiki/project/12-master-audit.md`, `DESIGN.md`, `interface-design.md`, `FRONTEND_WEBGL_AUDIT_REPORT.md`, and related unstaged documentation. This plan delivers a robust zero-trust publication pipeline, cross-language signature parity, WCAG 2.2 AA compliant frontend design system, Go sidecar timer optimization, and resilient WebGL lifecycle management.

## Architecture Decisions
- **Fail-Closed Publication Boundary**: The GitHub Pages deployment runner must install complete validation dependencies (`pydantic`, `pydantic-settings`, `httpx`, `cryptography`) in its isolated verification environment to prevent silent deployment failures leaving stale artifacts live.
- **Strict Byte-Envelope Parity**: Detached Ed25519 release signatures and WebCrypto verifiers must strictly agree on canonical UTF-8 JSON serialization without whitespace drift.
- **5-State Data Trust Model**: Frontend views never guess freshness or use visitor local clocks; all surfaces strictly reflect verified artifact state (*Loading, Fresh, Stale, Invalid, Empty/Error*).
- **Zero-Build Vanilla PWA**: Maintain modular ES6 architecture and Cold Luxury design tokens (`#0a0e17` background, `#3b82f6` cobalt, `#06b6d4` cyan) without introducing heavy external npm frameworks or build steps.
- **Bounded UDP Multiplexing**: Eliminate ephemeral `time.After` allocations in Go scanner packet receiver loops using reusable `time.NewTimer` instances.

---

## Task List

### Phase 1: Release Pipeline & Deployment Qualification (P0 Blockers)

#### Task 1: Close Deploy Runner Validator Runtime Dependencies
**Description:** Update `.github/workflows/deploy-pages.yml` to install all required validator dependencies (`pydantic>=2.0.0`, `pydantic-settings>=2.0.0`) in the `Install rollback verification dependencies` step, ensuring `validate_frontend_placeholders.py` executes without `ModuleNotFoundError`.

**Acceptance criteria:**
- [ ] `.github/workflows/deploy-pages.yml` installs `pydantic>=2.0.0` and `pydantic-settings>=2.0.0` alongside `httpx` and `cryptography`.
- [ ] `validate_frontend_placeholders.py --strict` executes cleanly in an isolated Python environment mimicking the deploy runner.
- [ ] `deploy-pages.yml` sealed artifact verification sets `DEPLOY_READY=true` upon successful validation.

**Verification:**
- [ ] Static validation passes: `python scripts/validate_frontend_placeholders.py --strict output`
- [ ] Workflow YAML syntax passes lint/parse check.

**Dependencies:** None  
**Files likely touched:**
- `.github/workflows/deploy-pages.yml`
- `scripts/validate_frontend_placeholders.py`  
**Estimated scope:** Small (2 files)

---

#### Task 2: Harden Cross-Language Ed25519 Byte Envelope & Negative Vectors
**Description:** Ensure exact UTF-8 canonical byte serialization parity between Python `src/configstream/signer.py` and browser WebCrypto in `frontend/assets/js/verifier.js`. Add comprehensive positive and negative test vectors.

**Acceptance criteria:**
- [ ] Python signer and JavaScript WebCrypto verifier consume identical canonicalized UTF-8 byte payloads for `artifact_manifest.json`.
- [ ] Unit tests verify signature generation and verification across cross-language test vectors.
- [ ] Negative test vectors confirm immediate rejection of tampered payloads, manipulated timestamps, and mismatched public keys.

**Verification:**
- [ ] Tests pass: `pytest tests/unit/test_signer.py`
- [ ] Cross-language test vector script passes in Node.js / browser environment.

**Dependencies:** None  
**Files likely touched:**
- `src/configstream/signer.py`
- `frontend/assets/js/verifier.js`
- `tests/unit/test_signer.py`  
**Estimated scope:** Medium (3 files)

---

#### Task 3: Enforce Trust Bootstrap Sequence Across All Frontend Surfaces
**Description:** Standardize script inclusion order (`runtime-config.js` -> `constants.js` -> `verifier.js` -> `artifact-guard.js`) across all 9 static HTML surfaces and add an automated structural regression test.

**Acceptance criteria:**
- [ ] All 9 public HTML pages load `runtime-config.js` first, followed by `constants.js`, `verifier.js`, and `artifact-guard.js`.
- [ ] No page permits operational subscription copy or download before public trust bootstrapping completes.
- [ ] Automated regression test in `tests/unit/test_frontend_structure.py` validates script tags and ordering on all `.html` files.

**Verification:**
- [ ] Tests pass: `pytest tests/unit/test_frontend_structure.py`
- [ ] Browser smoke test confirms trust initialization on all routes.

**Dependencies:** Task 2  
**Files likely touched:**
- `frontend/index.html`
- `frontend/proxies.html`
- `frontend/analytics.html`
- `frontend/lab.html`
- `tests/unit/test_frontend_structure.py`  
**Estimated scope:** Medium (5 files)

---

### Checkpoint: Foundation & Publication Gate
- [ ] Deploy runner dependency closure verified.
- [ ] Ed25519 cross-language signature test vectors pass cleanly.
- [ ] Script ordering test passes across all 9 HTML surfaces.

---

### Phase 2: Frontend Trust States, Design Tokens & Accessibility (P1)

#### Task 4: Implement 5-State Trust UI Contract in Core Controllers
**Description:** Update `main.js` and `proxies.js` to implement the 5-state UI contract (*Loading, Fresh, Stale, Invalid, Empty/Error*) with truthful metadata-derived timestamps and non-spoofed provenance banners.

**Acceptance criteria:**
- [ ] All views render skeleton loaders during data fetch with zero cumulative layout shift (CLS).
- [ ] Stale artifacts display a persistent warning banner citing `metadata.json` generation time (never visitor clock).
- [ ] Invalid/untrusted signatures block operational actions and render a fail-closed error dialog.
- [ ] Empty and network-error states provide descriptive diagnostics with actionable "Retry" triggers.

**Verification:**
- [ ] Unit/browser tests with mocked state fixtures: `pytest tests/unit/test_frontend_states.py`
- [ ] Manual inspection of simulated stale and invalid metadata states.

**Dependencies:** Task 3  
**Files likely touched:**
- `frontend/assets/js/main.js`
- `frontend/assets/js/proxies.js`
- `frontend/assets/js/state.js`  
**Estimated scope:** Medium (3 files)

---

#### Task 5: Consolidate Design Tokens, Fix Sticky Header Occlusion & Focus Visible
**Description:** Implement `DESIGN.md` design tokens in shared CSS, eliminate generic purple gradient overrides, add `scroll-margin-top` to all hash anchor targets, and enforce high-contrast `:focus-visible` styling.

**Acceptance criteria:**
- [ ] Shared CSS defines tokens: `--bg-base: #0a0e17`, `--bg-surface: #111827`, `--bg-glass`, `--accent-cobalt: #3b82f6`, `--accent-cyan: #06b6d4`, and status colors.
- [ ] All anchor sections (`#faq`, `#quick-search`, `#telemetry`) declare `scroll-margin-top: 80px` to prevent sticky header occlusion.
- [ ] Focus states render high-contrast cyan ring (`:focus-visible { outline: 2px solid #06b6d4; outline-offset: 2px; }`).
- [ ] `@media (prefers-reduced-motion: reduce)` disables non-essential animations.

**Verification:**
- [ ] CSS lint / automated style validation passes.
- [ ] Keyboard navigation and viewport walkthrough at 375px, 768px, 1024px, and 1440px.

**Dependencies:** None  
**Files likely touched:**
- `frontend/assets/css/style.css`
- `frontend/assets/css/tokens.css`
- `frontend/index.html`  
**Estimated scope:** Medium (3 files)

---

#### Task 6: Enforce Tabular Numerics & WCAG 2.2 AA Touch Targets
**Description:** Apply `font-variant-numeric: tabular-nums` to all telemetry and table columns, enforce $\ge 44\times44\text{px}$ mobile / $\ge 24\times24\text{px}$ desktop touch targets, and replace structural emojis with accessible SVG icons.

**Acceptance criteria:**
- [ ] `tabular-nums` applied to all ping latencies, IP addresses, port numbers, and counter metrics.
- [ ] All interactive buttons, mode tabs, and copy triggers meet touch target sizing.
- [ ] Structural emojis in core buttons and navigation replaced with Lucide/Simple Icons SVGs with `aria-label` or `aria-hidden="true"`.

**Verification:**
- [ ] Accessibility contrast and touch target automated audit.
- [ ] Visual verification of table rendering under dynamic latency updates.

**Dependencies:** Task 5  
**Files likely touched:**
- `frontend/assets/css/style.css`
- `frontend/proxies.html`
- `frontend/index.html`  
**Estimated scope:** Medium (3 files)

---

### Checkpoint: Frontend Trust & Visual Baseline
- [ ] 5-state trust contract verified via mock fixtures.
- [ ] Anchor links scroll safely beneath sticky header at all 4 responsive viewports.
- [ ] Focus rings and touch targets pass WCAG 2.2 AA standards.

---

### Phase 3: Live Verification & Data Plane Optimization (P1 / P2)

#### Task 7: Harden Live Candidate Identity Gate in Deployment Verifier
**Description:** Enhance `scripts/verify_pages_deployment.py` to compare live manifest against candidate commit SHA, run ID, manifest digest, and Ed25519 signature.

**Acceptance criteria:**
- [ ] `verify_pages_deployment.py` accepts candidate commit SHA, run ID, and manifest digest as CLI arguments.
- [ ] Verifier fetches live site with cache-busting headers and verifies signature against configured public key.
- [ ] Regression test verifies that a valid but outdated deployment is rejected.

**Verification:**
- [ ] Tests pass: `pytest tests/unit/test_verify_pages_deployment.py`
- [ ] Smoke test against local mock server serving fresh and stale deployments.

**Dependencies:** Task 1, Task 2  
**Files likely touched:**
- `scripts/verify_pages_deployment.py`
- `tests/unit/test_verify_pages_deployment.py`  
**Estimated scope:** Small (2 files)

---

#### Task 8: Optimize Go Scanner UDP Timer Allocations & Memory Churn
**Description:** In `src/go/tester/scanner/scanner.go`, eliminate ephemeral `time.After()` channel allocations inside the packet receiver select block by using reusable `time.NewTimer()` instances with `Reset()` calls.

**Acceptance criteria:**
- [ ] `time.After()` in packet receive select loop replaced with reusable `time.NewTimer` instance.
- [ ] Single-socket UDP multiplexing and `defer recover()` guards preserved.
- [ ] Zero channel allocation per received packet verified via Go benchmarks.

**Verification:**
- [ ] Benchmarks pass: `go test -v -bench=. -benchmem ./src/go/tester/scanner/...`
- [ ] Go test suite passes: `go test -v -race ./src/go/tester/...`

**Dependencies:** None  
**Files likely touched:**
- `src/go/tester/scanner/scanner.go`
- `src/go/tester/scanner/scanner_test.go`  
**Estimated scope:** Small (2 files)

---

#### Task 9: Remediate Broad Exceptions in Python Parsers & Adapters
**Description:** Refactor generic `except Exception:` blocks across `src/configstream/parsers/` and `src/configstream/adapters/` into explicit `(ValidationError, json.JSONDecodeError, TimeoutError, ValueError)` exception handlers.

**Acceptance criteria:**
- [ ] Generic `except Exception:` replaced with specific error tuples in core parsers (VLESS, VMess, Trojan, Shadowsocks) and converters.
- [ ] Error logging continues to sanitize sensitive fields via `SecurityValidator.sanitize_log_message()`.
- [ ] All parser unit tests pass with zero uncaught exception regressions.

**Verification:**
- [ ] Tests pass: `pytest tests/unit/test_parsers.py`
- [ ] Static type check passes: `mypy src/configstream`

**Dependencies:** None  
**Files likely touched:**
- `src/configstream/parsers/base.py`
- `src/configstream/parsers/vless.py`
- `src/configstream/parsers/vmess.py`
- `src/configstream/adapters/clash.py`  
**Estimated scope:** Medium (4 files)

---

### Checkpoint: Backend & Verifier Hardening
- [ ] `verify_pages_deployment.py` passes candidate verification and rejects stale fixtures.
- [ ] Go scanner benchmark shows zero timer channel allocations in packet receive loop.
- [ ] Python parser test suite passes with explicit exception handling.

---

### Phase 4: WebGL Performance, Throttling & Progressive Enhancements (P3)

#### Task 10: Globe.gl DPR Clamping, Offscreen Throttling & Context Recovery
**Description:** Clamp Globe.gl DPR to $\le 1.5$, attach `IntersectionObserver` to pause render loop when `#globe-viz` is offscreen, and add `webglcontextlost` / `webglcontextrestored` event handlers.

**Acceptance criteria:**
- [ ] `renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5))` configured in `analytics.js`.
- [ ] `IntersectionObserver` pauses auto-rotation and `requestAnimationFrame` when the globe container is scrolled out of view.
- [ ] `webglcontextlost` cancels RAF and logs warning; `webglcontextrestored` re-initializes scene cleanly.

**Verification:**
- [ ] Browser automated test verifying render loop suspension on scroll.
- [ ] Manual context loss simulation (`gl.getExtension('WEBGL_lose_context').loseContext()`).

**Dependencies:** Task 5  
**Files likely touched:**
- `frontend/assets/js/analytics.js`
- `frontend/assets/css/analytics.css`  
**Estimated scope:** Small (2 files)

---

#### Task 11: Procedural 3D Polyhedral Hero Node with Reduced Motion
**Description:** Implement zero-dependency Three.js procedural cryptographic node on `frontend/index.html` with physical shader, wireframe orbital cage, and reduced-motion fallback.

**Acceptance criteria:**
- [ ] Procedural Three.js icosahedron + wireframe mesh mounts cleanly in `#hero-3d-canvas`.
- [ ] Animation respects `prefers-reduced-motion: reduce` (renders static frame with no RAF loop).
- [ ] Teardown hook disposes geometries, materials, and renderer on route change / unmount.
- [ ] Core subscription copy flow remains 100% operational even if WebGL is unsupported.

**Verification:**
- [ ] Visual verification across light/dark themes and reduced-motion settings.
- [ ] Memory leak test checking heap after 10 mount/unmount cycles.

**Dependencies:** Task 5, Task 10  
**Files likely touched:**
- `frontend/assets/js/hero-node.js`
- `frontend/index.html`  
**Estimated scope:** Small (2 files)

---

#### Task 12: Master Readiness Ledger & Documentation Synchronization
**Description:** Update `docs/readiness.json`, `STATUS.md`, and wiki roadmap status to record verified evidence for all completed tasks and milestones.

**Acceptance criteria:**
- [ ] `docs/readiness.json` updated with test results, coverage figures, and release readiness gates.
- [ ] `STATUS.md` re-generated and consistent with machine-readable readiness state.
- [ ] All wiki links and C4 architecture references verified.

**Verification:**
- [ ] Validate readiness JSON schema: `python scripts/validate_pages_artifact.py output`
- [ ] Check link integrity across `docs/wiki/`.

**Dependencies:** Tasks 1–11  
**Files likely touched:**
- `docs/readiness.json`
- `STATUS.md`
- `docs/wiki/project/12-master-audit.md`  
**Estimated scope:** Medium (3 files)

---

### Checkpoint: Complete Delivery
- [ ] Full Python test suite passes (`pytest`).
- [ ] Full Go test suite & benchmarks pass (`go test -v ./src/go/...`).
- [ ] Frontend placeholder and pages validation passes (`python scripts/validate_frontend_placeholders.py --strict output`).
- [ ] `docs/readiness.json` reflects verified target state.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|:---|:---:|:---|
| **Deploy runner dependency mismatch** | High | Pinned versions in `deploy-pages.yml` with clean preflight validation. |
| **Cross-language signature byte divergence** | High | Standardized canonical UTF-8 JSON serialization with strict test vectors. |
| **Mobile GPU throttling / overdraw on WebGL** | Medium | DPR clamped to 1.5; offscreen pause via `IntersectionObserver`. |
| **High PPS UDP timer memory leaks** | Medium | Reusable `time.NewTimer` with explicit `Reset` calls verified by benchmarks. |
| **Sticky header content clipping on anchor links** | Low | Universal `scroll-margin-top: 80px` applied to all section IDs. |

---

## Open Questions
- None blocking Phase 1 execution. Optional procedural hero 3D node can be evaluated during Phase 4 without blocking core subscription delivery.
