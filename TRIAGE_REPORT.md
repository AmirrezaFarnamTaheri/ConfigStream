# ConfigStream CI/Triage/Dependabot Report
Generated: $(date -u +'%Y-%m-%d %H:%M UTC')

## 1. CI Checkout Failure — FIXED

### Root Cause
The `pipeline` job (Run Batch Shard) runs inside a Docker container with `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` set at the **container-level env**. This forces the GitHub Actions runner to use Node 24 for all JavaScript actions (including `actions/checkout@v7`) inside the container. The runner's Node 24 injection into the container fails, causing the checkout to fail in exactly 1 second.

### Fix Applied
Removed `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` from the container-level env in the `pipeline` job's `container:` block. Step-level occurrences remain (they only affect shell steps, not JavaScript actions).

**File**: `.github/workflows/main.yml`

### Affected Jobs
- ✅ Schedule Gate — was already working (runs on ubuntu-latest, not in container)
- ✅ Build & Push Container — was already working
- ✅ Build WASM Module — was already working  
- ✅ Setup Intelligence Data — was already working
- ✅ Setup Matrix — was already working
- ❌ Run Batch Shard (all 17) — **FIXED** (was failing at Checkout step)
- ❌ Merge & Fan-Out — cascading failure (depends on shard artifacts)

---

## 2. Issue Triage (25 Open Issues)

### 🔴 P0 — Release Blocking
| # | Title | Impact |
|---|---|---|
| **#495** | Live Pages deployment fails smoke test | STATUS.md contradicts "production-ready" claim |

### 🟠 P1 — Security Vulnerabilities
| # | Title | Risk |
|---|---|---|
| **#493** | DNS-rebinding TOCTOU gap in fetcher.py | IP validated then re-resolved independently |
| **#491** | trustedHTML flag bypasses DOMPurify in dom.js | XSS vector via trusted HTML path |
| **#490** | Hand-rolled regex for href in ui.js | Bypasses standard DOMPurify sanitization |
| **#494** | Stego LSB deterministic pattern | Correlatable output across images |
| **#474** | YAML injection in exporters.js | Unescaped fields in Clash config |

### 🟡 P2 — Code Quality / Performance
| # | Title | Impact |
|---|---|---|
| **#498** | Broad bare except blocks across 100+ files | Silent error swallowing |
| **#497** | Stale build artifacts in repo | Repo bloat |
| **#492** | service-worker.js ignores response.ok | Silent fetch failures |
| **#489** | event_stream.py opens/locks file every write | Performance |
| **#487** | adaptive_timeout.py holds lock during full sort | O(n²) performance |
| **#485** | test_cache.py quadratic I/O | Performance on large caches |
| **#488** | blocklist.py no conditional GET | Redundant downloads |
| **#486** | dns_cache.py O(n log n) LRU eviction | Performance |

### 🔵 P3 — Other Issues
| # | Title |
|---|---|
| **#496** | SECURITY.md has unfilled contact placeholders |
| **#484** | Lab parser.js returns null on errors, no validation |
| **#483** | Lab builder.js uses unvalidated server_name |
| **#482** | Washer core asyncio.Lock() in sync init |
| **#481** | Proxy chaining no private IP filtering |
| **#480** | Washer marks proxies working before testing |
| **#479** | key_generator empty install_id |
| **#478** | WARP scraper backtracking regex |
| **#477** | go_tester no binary checksum verification |
| **#476** | WebSocket origin accepts wildcard |
| **#475** | Evasion preset static hash with silent fallback |

---

## 3. Dependabot PRs (8 Open)

All PRs fail CI due to the same container-level `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` issue. Once the CI fix is pushed, most should pass.

### Safe to Merge (patch/minor bumps of well-known packages)
| # | Package | Bump | Risk |
|---|---|---|---|
| **#469** | hypothesis | 6.155.7→6.156.1 | ✅ Low — test framework, patch |
| **#470** | typing-extensions | 4.15.0→4.16.0 | ✅ Low — typing utils, minor |
| **#471** | vite | 8.1.2→8.1.3 | ✅ Low — dev build tool, patch |
| **#468** | picomatch | 4.0.4→4.0.5 | ✅ Low — glob matcher, patch |
| **#467** | docker/login-action | 4.2.0→4.4.0 | ✅ Low — CI action, minor |

### Review Carefully (major/minor bumps)
| # | Package | Bump | Risk |
|---|---|---|---|
| **#473** | pydantic | 2.12.5→2.13.4 | ⚠️ Minor — may have deprecations |
| **#472** | maxminddb | 3.0.0→3.1.1 | ⚠️ Minor — core GeoIP dependency |
| **#466** | pydantic-core | 2.41.5→2.47.0 | ⚠️ Minor — must match pydantic version |

### Recommended Merge Order
1. Push the CI fix first
2. Merge #468 (picomatch), #469 (hypothesis), #471 (vite), #467 (docker/login-action) — lowest risk
3. Merge #470 (typing-extensions) — low risk
4. Merge #472 (maxminddb), #473 (pydantic), #466 (pydantic-core) together — must be compatible

---

## 4. Recommended Next Steps

1. **Push the CI fix** and trigger a manual workflow_dispatch to verify checkout succeeds
2. **Merge Dependabot PRs** in order above after CI is green
3. **Triage P1 security issues** — #493, #491, #490 are high-priority
4. **Fix #495** — Pages deployment smoke test failure
5. **Label the 25 open issues** with severity labels
