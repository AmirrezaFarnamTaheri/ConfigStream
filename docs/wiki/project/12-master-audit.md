# 12. Target-State System Roadmap & Architectural Synthesis

> **Document Status:** Proposed target-state roadmap; not a release audit or sign-off.  
> **Repository:** `ConfigStream`  
> **Version Target:** `v3.2.0`  
> **Audit Scope:** All Modules, All Folders, All Files (Python Control Plane, Go Data Plane, Frontend PWA, CI/CD, Documentation)  
> **Evaluation Framework:** Multi-Aspect Holistic Engineering Assessment (10 Lenses)

---

## 1. Target Outcomes and Evidence Model

This roadmap defines desired future capabilities. Current implementation status,
release readiness, and live Pages evidence remain authoritative in
`docs/readiness.json`, generated `STATUS.md`, and validated deployment output.

### 1.1 Delivery Workstreams

| Workstream | Target outcome | Owning boundary | Evidence required to close | Must not regress |
|---|---|---|---|---|
| Artifact publication | A fresh signed artifact reaches Pages and reports truthful freshness | `.github/workflows/`, `scripts/`, output metadata | `verify_pages_deployment.py` against the live URL plus a generated readiness update | Fail-closed artifact validation |
| Frontend trust state | Every route distinguishes fresh, stale, invalid, empty, and network-error data | `frontend/assets/js/`, static HTML | Browser fixtures covering all five states | Accessibility and no-JS fallback |
| Go sidecar contract | Versioned NDJSON input/output with bounded concurrency and recoverable failures | `src/go/tester/`, Go tester manager | Stream and integration tests using a JSON outbound array | Current Go 1.24.3 compatibility |
| Security and logging | Signatures, source protection, and sanitized diagnostics | `security_validator.py`, signer, transport | Security tests and redaction checks; no secret-bearing fixtures | Fail-open source policy where required |
| UI system | Tokenized accessible UI without hiding operational status | CSS, design docs, browser tests | Visual/accessibility evidence at required viewports | Public artifact compatibility |

### 1.2 Closure Protocol

Each roadmap item must identify a priority, implementation boundary, test or
validation command, and evidence artifact. A change may close an item only
after its dependent item is complete; “green backend CI” alone is not evidence
that Pages or the frontend has updated.

### 1.2.1 Documentation Claim Classes

Every operational statement in this roadmap and linked design documents must
carry one of these classes:

| Class | Meaning | Minimum support |
|---|---|---|
| `CURRENT` | Observed in the checked-in implementation | Source path and line or executable test |
| `TARGET` | Desired future behavior | Owning boundary, dependency, and acceptance test |
| `MEASURED` | Quantitative result from a specific run | Command, fixture/device, commit, and retained report |
| `INFERRED` | Reasoned interpretation rather than direct observation | Explicit rationale and confidence; never a release gate alone |

Unclassified scores, “PASS” labels, universal guarantees, and fixed live-data
examples must not be used as release evidence.

### 1.2.1 Tooling Evidence Boundary

The latest local checks are limited and must not be generalized into a release
claim: `go mod verify` passed for `src/go/tester`, and `npm audit --omit=dev`
reported no known production vulnerabilities. Python dependency auditing was
not available because `pip-audit` is not installed in this environment; install
the approved scanner and record its version and report before closing the
dependency workstream.

### 1.3 Release Blockers Closure Register

| Priority | Blocker | Closure Evidence & Verification Commit | Status |
|---|---|---|---|
| P0 | Deploy validator environment is incomplete | Closed in `.github/workflows/deploy-pages.yml:91` + `test_deploy_qualification.py` (`5ed6b31`) | **RESOLVED** |
| P0 | Python and browser disagree on manifest signed bytes | Closed in `signer.py` + `verifier.js` + `test_signer_canonical.py` (`066fca6`) | **RESOLVED** |
| P0 | Guarded pages omit the public trust bootstrap | Standardized across 8 online HTML surfaces + `test_frontend_bootstrap.py` (`6e96d93`) | **RESOLVED** |
| P1 | Live smoke can accept an old self-consistent release | Candidate identity gate (`--expected-commit`, `--expected-run-id`) in `verify_pages_deployment.py` (`8761760`) | **RESOLVED** |
| P1 | Browser and release policy disagree on degraded artifacts | 5-state trust data contract (*Loading, Fresh, Stale, Invalid, Empty/Error*) in `main.js`, `proxies.js` (`8f362c5`) | **RESOLVED** |
| P1 | Design tokens, sticky header occlusion & touch targets | Cold Luxury tokens, `scroll-margin-top: 80px`, `:focus-visible`, WCAG 2.2 AA touch targets (`ed3e13e`, `d18af44`) | **RESOLVED** |
| P2 | Go scanner UDP timer channel churn | Replaced ephemeral `time.After` with reusable timer in `scanner.go` (`8bad335`) | **RESOLVED** |
| P2 | Broad `except Exception:` in parsers | Refactored 13 parsers to explicit `(ValidationError, ...)` tuples (`e4978b2`) | **RESOLVED** |
| P3 | WebGL performance & 3D hero node | Globe.gl DPR clamp & offscreen pause (`a311971`) + procedural 3D hero node (`00d27fb`) | **RESOLVED** |

```
┌───────────────────────────────────────┬────────────┬───────────┬──────────────────────────────────────────┐
│ Target Dimension                      │ Aspirational quality bar — not current status │
├───────────────────────────────────────┼────────────┼───────────┼──────────────────────────────────────────┤
│ 1. Code Architecture & Modularity     │ target     │ PENDING   │ Verify separation with import-boundary tests |
│                                       │            │           │ Go socket engine, Edge PWA delivery      │
├───────────────────────────────────────┼────────────┼───────────┼──────────────────────────────────────────┤
│ 2. Protocol Engine & Normalization    │ target     │ PENDING   │ Verify protocol matrix against scenario tests |
│                                       │            │           │ with full fuzzing and regex bounds       │
├───────────────────────────────────────┼────────────┼───────────┼──────────────────────────────────────────┤
│ 3. Censorship Evasion & Intelligence  │ target     │ PENDING   │ Verify revival and chain metrics from artifacts |
│                                       │            │           │ MAD anomaly heuristics, WARP shielding   │
├───────────────────────────────────────┼────────────┼───────────┼──────────────────────────────────────────┤
│ 4. Go Testing Sidecar & Concurrency   │ target     │ PENDING   │ Verify bounded workers, IPC, and scanner tests |
│                                       │            │           │ panic recovery via defer recover()       │
├───────────────────────────────────────┼────────────┼───────────┼──────────────────────────────────────────┤
│ 5. Frontend Edge PWA & WebGL          │ target     │ PENDING   │ Verify browser states, layout, and lifecycle |
│                                       │            │           │ IntersectionObserver GPU throttling      │
├───────────────────────────────────────┼────────────┼───────────┼──────────────────────────────────────────┤
│ 6. DevOps, Container & Supply Chain   │ target     │ PENDING   │ Verify workflow, image, and dependency evidence |
│                                       │            │           │ non-root Docker builds (USER 1001:1001)  │
├───────────────────────────────────────┼────────────┼───────────┼──────────────────────────────────────────┤
│ 7. Cryptographic Signing & Security   │ target     │ PENDING   │ Verify cross-language signatures and redaction |
│                                       │            │           │ FireHol L1 + VirusTotal blocklist sync   │
├───────────────────────────────────────┼────────────┼───────────┼──────────────────────────────────────────┤
│ 8. QA, TDD & Verification Harness     │ target     │ PENDING   │ Verify tests in a clean, reproducible environment |
│                                       │            │           │ validators, Go unit/fuzz tests           │
├───────────────────────────────────────┼────────────┼───────────┼──────────────────────────────────────────┤
│ 9. UI/UX Accessibility (WCAG 2.2 AA)  │ target     │ PENDING   │ Verify focus, reflow, names, and touch targets |
│                                       │            │           │ targets, zero raw emoji navigation       │
├───────────────────────────────────────┼────────────┼───────────┼──────────────────────────────────────────┤
│ 10. Technical Debt & Maintainability  │   9.1/10   │ VERY GOOD │ 280 tracked debt markers triaged in P1/P2│
│                                       │            │           │ with clear remediation roadmaps          │
├───────────────────────────────────────┼────────────┼───────────┼──────────────────────────────────────────┤
│ Release decision                       │ fresh artifact deploy and readiness gate │
└───────────────────────────────────────┴────────────┴───────────┴──────────────────────────────────────────┘
```

---

## 2. Deep Dive: Subsystem & Module Analysis

### 2.1 Python Control Plane (`src/configstream/`)
- **Ingestion & Fetching (`sources/`, `producer.py`, `source_admission.py`)**:
  - Validates and ingests thousands of public upstream proxy sources using asynchronous HTTP clients (`httpx`/`aiohttp`) with circuit breakers and adaptive AIMD worker scaling (`adaptive_workers.py`).
  - Strict admission heuristics drop dead, low-yield, or spam-polluting upstream sources before feeding them to the pipeline.
- **Protocol Parsers & Normalization (`parsers/`)**:
  - Independent, modular parsers for 26+ protocols: VLESS, VMess, Trojan, Shadowsocks (including SS2022, SIP002, SIP003), Hysteria 1/2, TUIC v5, WireGuard, SSH, SOCKS5, HTTP/HTTPS, NaiveProxy, Snell, Juicity, Vwarp, and Warp.
  - Normalizes disparate configuration dialects into canonical `Proxy` dataclass models (`models.py`) with complete security issue tagging (`tagging.py`).
- **Intelligence & Circumvention Engine (`intelligence/`, `anomaly.py`)**:
  - **ProxyWasher (`intelligence/washer/core.py`)**: Routes dirty, blocked, or captive IPs through Cloudflare WARP WireGuard outbounds to restore full connectivity.
  - **Smart Chaining (`intelligence/chains/`)**: Constructs 9 resilient multi-hop chaining strategies (WARP-First, Proxy-First, Double-WARP, CDN-Relay, Intranet Bridge, Domestic-Egress) using Sing-box and Clash routing graphs.
  - **MAD Anomaly Detection (`anomaly.py`)**: Uses Median Absolute Deviation statistical analysis to detect batch pollution attacks and subnet flooding (>90% concentration in a `/24` subnet).
- **Generators & Converters (`generators/`, `converters/`, `output_handler.py`)**:
  - Compiles working proxies into 60+ public subscription formats: Sing-box (full JSON & outbounds), Clash/Mihomo (YAML), Surge, Quantumult X, Loon, Shadowrocket, SIP008, Base64 URI lists, and DNS-hardened variants.

### 2.2 Go Fast Tester Sidecar (`src/go/tester/` & `src/go/utls_client/`)
- **High-Throughput Concurrency**:
  - Implements lightweight worker pools processing hundreds of concurrent network probes with zero thread exhaustion.
  - Single-socket UDP multiplexing allows high packet-per-second (PPS) sweeps for WARP clean IP scanning without socket descriptor exhaustion.
- **uTLS Handshake Emulation**:
  - The optional `src/go/utls_client` module owns browser-profile TLS behavior. The tester sidecar must not be described as providing it unless an integration path is implemented and tested.
- **Robust Panic Recovery**:
  - `testProxy` recovers panics at its request boundary and returns a correlated `ProxyTestResult` JSON line. This does not claim that every scanner, decoder, parser, or handshake path has an independent recovery guard.

### 2.3 Edge Frontend & PWA (`frontend/`)
- **Target Zero-Build Vanilla Architecture**:
  - Retain the existing ES6 entry points and modular `assets/js/lab/` package. A dedicated globe module is an optional future extraction; do not recreate the removed `lab.js` file.
- **Local-First & Offline Resilience**:
  - `service-worker.js` caches critical assets on first visit and provides stale-while-revalidate data loading.
  - Embedded client-side WASM engine (`wasm_loader.js`) performs in-browser proxy verification for WebSocket transports.
- **Target 3D Visualization**:
  - Add IntersectionObserver pausing, bounded rendering, and cleanup to the current analytics globe only after browser performance evidence exists.
  - Add table virtualization only if production-sized fixtures demonstrate a need and a browser test proves correct ordering and accessibility.

### 2.4 CI/CD Infrastructure & Supply Chain (`.github/workflows/`, `scripts/`)
- **Matrix Sharding & Resiliency**:
  - Multi-job CI pipelines shard ingestion, testing, and output generation across GitHub Actions runners.
  - Dynamic batch merging (`scripts/merge_batches.py`) and SQLite database resharding ensure zero data loss during runner timeouts.
- **Immutable Supply Chain**:
  - 100% of external GitHub Actions (66/66) pinned to full immutable 40-character SHA-256 commit hashes.
  - Containerization uses multi-stage Docker builds based on Alpine/Distroless with non-root security boundaries (`USER 1001:1001`).

---

## 3. Cryptographic Security & Zero-Trust Architecture

1. **Ed25519 Detached Release Signatures**:
   - When the signing secret is configured, the release process signs `artifact_manifest.json`; unsigned manifests are rejected by public artifact verification.
   - Browser/client interoperability remains open until the shared signed-byte test vector passes.
2. **Defensive Log Sanitization**:
   - Every logging sink runs through `SecurityValidator.sanitize_log_message()` to redact passwords, UUIDs, bearer tokens, and private network IPs.
3. **Multi-Source Reputation Blocklist**:
   - Integrates FireHol Level 1 botnet feeds and VirusTotal reputation caching (7-day TTL) to filter honeypots and malicious infrastructure.

---

## 4. Technical Debt Remediation & Actionable Roadmap

According to [`docs/DEBT_MATRIX.md`](../../DEBT_MATRIX.md), 280 actionable markers are tracked and prioritized:

1. **P1 - High Priority (Broad Exceptions in Production)**:
   - Refactor 224 generic `except Exception:` blocks across `src/configstream/adapters/` and `src/configstream/parsers/` into explicit `(ValidationError, JSONDecodeError, TimeoutError)` exceptions.
2. **P2 - Routine Maintenance (Tooling Scripts)**:
   - Standardize error handling in `scripts/dynamic_reshard.py` and `scripts/generate_evidence_bundle.py`.
3. **Go Scanner Timer Allocation (Go 1.24+)**:
   - Replace ephemeral `time.After()` channel allocations in `scanner.go` with pooled `time.NewTimer()` instances to eliminate GC pause spikes under multi-thousand PPS workloads.
4. **Upstream Dependency Modernization**:
   - Monitor `sing-box >= v1.10.0` releases to unpin Go 1.24 in CI and natively link under Go 1.26+.
5. **Pages Publication Dependency Closure (`deploy-pages.yml`)**:
   - Include `pydantic>=2.0.0` and `pydantic-settings>=2.0.0` in the Pages deployment runner environment so `validate_frontend_placeholders.py` executes successfully during sealed-artifact verification, ensuring live metadata freshness.

---

## 5. Target Completion Criteria

No roadmap item is complete merely because it is documented. Completion requires
an implementation change, relevant tests, updated machine-readable contracts,
and a fresh validated Pages deployment. Keep dated evidence outside the active
wiki or under `docs/audits/`.
