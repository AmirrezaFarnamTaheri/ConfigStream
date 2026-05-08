# ConfigStream Master Audit Report - Main Source Of Truth

**Audit date:** 2026-05-03
**Repository:** `C:\Users\ACER\Documents\GitHub\ConfigStream`
**Status:** Not production-ready, not ready-to-publish, and not currently trustworthy as a public release surface until the P0/P1 items in this report are closed.
**Purpose:** Replace the previous accumulated audit/addendum document with one clean, current, cohesive, evidence-based source of truth.

---

## 1. Executive Verdict

ConfigStream has a serious and valuable architecture: asynchronous ingestion, parser coverage across many proxy protocols, Go/Python testing paths, WARP/Vwarp washing and shielding ideas, static output publication, frontend analytics, a user-facing Laboratory, schema files, many tests, and extensive documentation.

The project is not currently in final production or ready-to-publish condition because its trust surface is split across conflicting truths:

1. The local Python suite can pass, but five GitHub workflow files do not parse as YAML.
2. Public GitHub Pages artifacts are stale and collapsed to one visible working proxy subscription.
3. Current repository schemas and generated public metadata do not match.
4. Runtime output metrics inflate `total_working` by counting untested shielded chains as working.
5. The deployed frontend path bypasses the Vite build output and serves raw static files with placeholder key material.
6. Security defaults and docs overclaim fail-closed behavior while admin auth, CORS, private IP policy, external QR generation, and lab test endpoints remain too permissive.
7. Documentation, status files, roadmap files, wiki pages, README tables, and frontend strategy lists disagree.
8. Several generated governance artifacts contain machine-local paths and self-referential noise.

The most important conclusion is this: **do not add more features until the project has one canonical contract per surface and every change is proven across backend, frontend, docs, schemas, tests, CI, and deployed artifacts.** Every capability claimed in project documents must either be completed, tested, documented, and published, or the claim must be removed until it is real.

---

## 2. Audit Method

This pass combined document review, repository inventory, source inspection, command-based validation, public artifact checks, and targeted scans.

Commands and checks run during the audit:

- `git status --short`
- `git ls-files`
- Markdown/document inventory
- YAML parsing for `.github/workflows/*.yml`
- `compileall -q src scripts tests`
- `pytest`
- `flake8 src tests`
- `black --check .`
- `mypy .`
- `npm ci`
- `npm audit --json`
- `npm run build`
- public artifact fetches from GitHub Pages:
  - `https://amirrezafarnamtaheri.github.io/ConfigStream/metadata.json`
  - `https://amirrezafarnamtaheri.github.io/ConfigStream/base64.txt`
  - `https://amirrezafarnamtaheri.github.io/ConfigStream/chosen/base64.txt`
  - `https://amirrezafarnamtaheri.github.io/ConfigStream/base64-dns-safe.txt`
- targeted source scans for:
  - workflow syntax, triggers, permissions, container user, and deployment logic
  - admin/auth/CORS/WebSocket/API endpoints
  - output metadata accounting
  - parser and tester invariants
  - frontend external dependencies, placeholders, and `innerHTML`
  - docs drift
  - generated debt artifacts
  - removed/deprecated paths
  - blocking filesystem calls in async code
  - log sanitization gaps

Repository inventory observed:

- 560 tracked files
- 290 Python files
- 70 Markdown files
- 58 JavaScript files
- 38 text files
- Major tracked areas:
  - `tests`: 150 files
  - `src`: 137 files
  - `frontend`: 96 files
  - `docs`: 56 files
  - `sources`: 34 files
  - `scripts`: 26 files
  - `tools`: 15 files
  - `.github`: 7 files

Validation results:

- Python compile: passed.
- `pytest`: 823 passed, 4 skipped after installing project dev dependencies.
- `flake8 src tests`: passed.
- `black --check .`: passed.
- `mypy .`: passed, with notes that many untyped function bodies are not checked.
- `npm ci`: completed, but `npm audit` reports 3 vulnerabilities.
- `npm run build`: passed, but deploy does not use `frontend-dist`.
- Workflow YAML parse: 5 failing workflows, 1 valid workflow.
- Public Pages artifacts: reachable but stale and collapsed.

---

## 3. Severity Model

**P0 - Release blocker:** Cannot call the project production-ready until fixed. Breaks CI/deploy/public trust/security fundamentals.

**P1 - High priority:** Serious production, security, reliability, or contract issue. Must be closed before public-ready status.

**P2 - Medium priority:** Important maintainability, correctness, or degraded-mode issue. Must be planned and tracked.

**P3 - Cleanup:** Hygiene, docs, portability, or lower-risk cleanup. Still required for a neat final state.

Closure standard for every item:

1. Source proof: exact files changed and why.
2. Runtime proof: commands run and results.
3. Regression proof: automated tests added or updated.
4. Cross-surface proof: backend, frontend, docs, schema, tests, CI, and deploy contract all agree.
5. Cleanup proof: no stale compatibility shim, duplicate helper, deprecated file, old doc claim, generated artifact, or unused path remains.
6. Changelog proof: `CHANGELOG.md` updated with what changed, why, tests run, breaking cleanup, and public contract effect.

---

## 4. Non-Negotiable Remediation Rules

These rules apply after every remediation step in the roadmap.

### 4.1 Cross-Surface Parity Gate

After each change, verify parity across:

- Backend implementation
- Frontend implementation
- Static deployed files
- Schemas
- Tests
- README
- Wiki docs
- SECURITY/STATUS/CHANGELOG
- CI workflow gates
- Public artifact names and shapes

No item is closed if one surface says the old truth and another surface says the new truth.

### 4.2 No Split-Brain Contracts

Every public concept must have one canonical owner:

- `proxies.json` shape
- `metadata.json` shape
- output file list
- lab strategy list
- protocol support matrix
- WARP/Vwarp behavior
- revived/shielded/smart-chain accounting
- public key/stego key injection
- CI/deploy release gates
- source shard count and reshard behavior

Delete duplicate definitions once the canonical owner exists.

### 4.3 No Permanent Backward-Compatibility Debt

This roadmap intentionally favors a clean final state over indefinite backward compatibility. Temporary migrations are allowed only inside the same pull request or same release step, and only if they are deleted before the item is marked done.

Required cleanup after each change:

- Delete old aliases.
- Delete deprecated files.
- Delete stale docs.
- Delete unused tests.
- Delete unused frontend branches.
- Delete fallback code that preserves a removed contract.
- Delete generated files that no longer represent the repo.
- Remove references to removed paths from docs, tests, workflows, and comments.

### 4.4 Concurrency And Race-Safety Gate

Every change touching workflows, pipeline, producer/consumer, output writes, websocket broadcast, cache, history, source quality, or tester lifecycle must explicitly check:

- no self-triggering workflow loops
- no overlapping deploys publishing mixed artifacts
- no concurrent writes to the same output path without atomic write or lock
- no unbounded queue or unbounded connection fanout
- no stale background task left running after shutdown
- no race between artifact generation and frontend copy
- no stale old artifact mixed into a new deploy
- no partial schema migration
- no shared mutable state accessed without a lock when used across threads/tasks

### 4.5 Changelog Rule

After every remediation step, update `CHANGELOG.md` with:

- summary
- motivation
- files changed
- public contract changes
- removed legacy/deprecated behavior
- tests and commands run
- cross-surface parity confirmation
- migration notes, if any
- remaining follow-up, if any

---

## 5. P0 Findings

### P0-1. Five GitHub workflow files are invalid YAML

Files:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy-pages.yml`
- `.github/workflows/deploy_mirror.yml`
- `.github/workflows/main.yml`
- `.github/workflows/retest.yml`

Observed state:

- YAML parsing fails with `ScannerError: mapping values are not allowed here`.
- The common pattern is `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` incorrectly indented under `env:`.
- `release.yml` parses successfully.

Concrete examples:

- `.github/workflows/main.yml` lines 30-34:
  - `env:` appears at the step level.
  - `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` is not nested under the same mapping depth as the other env keys.
- `.github/workflows/deploy-pages.yml` lines 41-43 has the same pattern.
- `.github/workflows/ci.yml` lines 14-16 has the same pattern.

Impact:

- CI cannot be trusted.
- Deployment cannot be trusted.
- Retest cannot be trusted.
- Mirror deployment cannot be trusted.
- Any claim that "workflows are green" is currently invalid.
- Security, style, test, schema, Pages, and release gates tied to these workflows may never execute.

Required fix:

1. Repair indentation in all workflows.
2. Run YAML parser on every workflow.
3. Add `actionlint`.
4. Add a repo script that parses every workflow in CI and locally.
5. Add a pre-commit hook for workflow parse/lint.
6. Update `STATUS.md`, `CHANGELOG.md`, `docs/wiki/project/05-devops.md`, and any CI badge/docs claim.

Closure checklist:

- `actionlint` passes.
- YAML parser passes all `.github/workflows/*.yml`.
- GitHub Actions UI recognizes all workflows.
- CI, deploy, retest, mirror, and release workflows can be manually dry-run or validated.
- Changelog includes the workflow parse fix and lists all repaired files.

---

### P0-2. Public deployment is stale, collapsed, and schema-inconsistent

Live public artifact check on 2026-05-03:

- `metadata.json`: HTTP 200, `Last-Modified: Sun, 22 Feb 2026 17:23:38 GMT`
- `metadata.generated_at`: `2026-02-22T17:22:48.495777+00:00`
- `base64.txt`: 152 bytes
- `chosen/base64.txt`: 152 bytes
- `base64-dns-safe.txt`: 152 bytes
- all three Base64 files are identical
- decoded subscription:

```text
socks5://Og%3D%3D@121.169.46.116:1090#%F0%9F%8C%90%20%7C%20SOCKS5%2BTCP%20%7C%201011ms%20%7C%20UP%20%7C%20NATIVE
```

Live metadata contradictions:

- `working`: 1
- `chosen_subset_size`: 1
- `total_working`: 857
- `shielded_count`: 856
- `total_proxies`: 1717
- `final_count`: 861
- `success_rate`: `2.5987525987525989E-05`
- `time_limited`: true
- `duration_seconds`: 273946.40592700004

Current repo schema mismatch:

- `schema/metadata.schema.json` requires `trace_id`, `backpressure_drop`, `total_sources`, and `pipeline_execution_audit`.
- Live public `metadata.json` lacks those required fields.

Impact:

- Users see stale data for months.
- Public subscriptions collapse to one proxy.
- Metadata claims many working entries while visible universal output has one entry.
- Current repo schema cannot be assumed to validate deployed metadata.
- The frontend and external consumers have no reliable health signal explaining degraded state.

Required fix:

1. Repair workflow deploy path first.
2. Add `artifact_manifest.json` with every public file, size, hash, count, schema version, generated time, degraded status, and reason.
3. Add `health.json` with freshness, time-limited flag, last successful full run, last successful deploy, and current degraded reason.
4. Add schema validation for public artifacts before deploy.
5. Add public artifact smoke tests after deploy.
6. Ensure stale public artifacts are clearly marked as stale if reused.

Closure checklist:

- Public metadata validates against current schema.
- Public Base64/chosen/DNS-safe outputs have documented expected relationships.
- Public `health.json` explains if outputs are degraded.
- Dashboard shows accurate freshness.
- `STATUS.md` no longer claims healthy if public artifacts are stale.
- Changelog records public artifact contract changes.

---

### P0-3. Scheduled pipeline can self-trigger source optimization commits

Evidence:

- `.github/workflows/main.yml` triggers on push to `main`, schedule, pull request, and workflow dispatch.
- The same workflow runs `python scripts/dynamic_reshard.py`.
- It commits changed `sources/batch_*.txt`.
- It pushes back to the current branch.
- There is no reliable `paths-ignore` or skip marker protecting the expensive pipeline from source-only bot commits.

Impact:

- Scheduled runs can trigger follow-on push runs.
- Artifact provenance becomes confusing.
- CI minutes are wasted.
- Runs can overlap with deploy or retest.
- Source quality and reshard data can race with active pipeline state.

Required fix:

1. Move resharding into a separate manual or low-cost workflow.
2. Publish reshard recommendations as artifacts before auto-committing them.
3. Add `paths-ignore` for source-only automation commits where appropriate.
4. Use `[skip ci]` only if policy permits and it does not hide necessary checks.
5. Add workflow concurrency groups that prevent mixed artifact publication.
6. Add a source-reshard lock or version marker so reshard decisions are tied to a completed run.

Closure checklist:

- One scheduled run cannot cause another full scheduled-equivalent run.
- Reshard commits cannot overlap with deploy of a different artifact generation.
- Run ID and trace ID are written into metadata and artifacts.
- Changelog records the new workflow ownership model.

---

### P0-4. Deploy workflow fails closed on sparse outputs

Evidence:

- `.github/workflows/deploy-pages.yml` copies raw `frontend/.` into `output/`.
- It requires many output files to exist.
- It requires many output files to be non-empty.
- Missing or empty files cause `exit 1`.

Impact:

- During hostile network conditions or time-limited runs, the project may publish nothing.
- This conflicts with the project rule that outputs are always generated.
- The deploy gate treats "not enough working proxies" as fatal rather than degraded.
- Users lose access to stale-known-good or partial-but-valid outputs exactly when the network is unreliable.

Required fix:

1. Replace non-empty checks with schema-valid degraded artifacts.
2. Generate empty-but-valid JSON/YAML/text outputs with clear degraded metadata.
3. Preserve stale-known-good artifacts only if explicitly labeled and hash-tracked.
4. Fail deploy only on invalid schema, unsafe content, missing manifest, or impossible provenance.
5. Add tests for zero-working-proxy deploy.

Closure checklist:

- Zero working proxies still produce valid outputs.
- Deploy succeeds with `health.status = degraded` when appropriate.
- The frontend renders the degraded state without placeholders.
- Changelog records fail-open/fail-safe deploy policy.

---

## 6. P1 Findings

### P1-1. Shielded chains are counted as working without retest

Evidence:

- `src/configstream/output_handler.py` builds `failed_proxies = [p for p in optimized_proxies if not p.is_working]`.
- It calls `washer.shield_batch(failed_proxies, stats=stats)`.
- It sets `stats.shielded_count = len(shielded_ids)`.
- `src/configstream/intelligence/washer/core.py` `shield_batch()` generates WARP/relay chain outbounds but does not retest them.
- `src/configstream/output_logic.py` computes:
  - `total_proxies = total + smart_chain_count + shielded_count`
  - `total_working = working + shielded_count`

Impact:

- Failed proxies wrapped into untested chains become counted as working.
- Live metadata shows this exact inflation: `working=1`, `shielded_count=856`, `total_working=857`.
- Frontend analytics, success rates, and public trust signals become misleading.

Required fix:

1. Separate `working`, `revived_working`, `shielded_candidates`, `shielded_tested`, and `shielded_working`.
2. Do not add untested shielded candidates to `total_working`.
3. If keeping failed shielded candidates for user experimentation, label them as `is_working=false` and `process=shielded-candidate`.
4. Retest shielded chains before counting them as working.
5. Add tests for metric invariants.

Closure checklist:

- `total_working <= total_tested` unless explicitly documented otherwise.
- `total_working` never includes untested chains.
- Frontend labels candidate chains separately from working chains.
- Public metadata explains candidate vs verified counts.
- Changelog records the metric contract correction.

Remediation progress:

- `src/configstream/output_logic.py` no longer adds `shielded_count` to `total_working`.
- `src/configstream/pipeline_stats.py` no longer adds `shielded_count` to `total_proxies`.
- Metadata now exposes `shielded_candidate_count` and `shielded_verified_count`; `shielded_count` remains as the candidate-count compatibility field.
- Frontend analytics/statistics comments now describe `total_working` as retested working proxies only.
- `tests/unit/test_output.py` includes a regression test proving shielded candidates do not inflate working totals or success rate.

Remaining:

- Retest shielded chains before any future nonzero `shielded_verified_count`.
- Update user-facing frontend labels where visual copy implies shielded candidates are verified working.

---

### P1-2. Admin notification endpoint is fail-open when no key is configured

Evidence:

- `src/configstream/server.py` enforces the API key only inside `if api_key:`.
- `ADMIN_API_KEY` defaults to `None`.
- If no key is configured, the endpoint broadcasts update notifications.

Impact:

- Production misconfiguration becomes unauthenticated control-plane access.
- Attackers could trigger update notifications and client churn.
- Docs imply stronger admin protection than the code guarantees.

Required fix:

1. In production, require `ADMIN_API_KEY`.
2. Fail startup if production has no admin key.
3. Allow unauthenticated admin calls only in explicit local/test mode.
4. Add rate limiting to admin endpoints.
5. Add tests for production without key, production with bad key, production with good key, and local opt-in behavior.

Closure checklist:

- Production without `ADMIN_API_KEY` fails closed.
- Docs mark the key as required for production.
- `.env.example` reflects the required key.
- Changelog records the breaking production-auth change.

Remediation progress:

- `/api/admin/notify-update` now rejects production calls when `ADMIN_API_KEY` is unset.
- Production calls must include a matching `api_key` payload when `ADMIN_API_KEY` is configured.
- Unauthenticated admin notifications are allowed only in explicit `development`, `ci`, or `test` environments.
- `/api/admin/notify-update` now has a `10/minute` SlowAPI limit.
- Server startup now fails in production when `ADMIN_API_KEY` is unset.
- `tests/unit/test_server.py` covers production without configured key, production missing payload key, production valid key, and explicit development no-key behavior.
- `tests/unit/test_server.py` verifies rate-limit registration for the admin notification route.
- `tests/unit/test_server.py` covers startup validation for production no-key, production keyed, and development no-key modes.
- `SECURITY.md` now marks `ADMIN_API_KEY` as required for production admin endpoints.

Remaining:

- None for the admin notification fail-closed finding. Follow-up CORS, WebSocket lifecycle, and lab endpoint hardening remain separate P1 items.

---

### P1-3. CORS default allows broad credentialed GitHub Pages origins

Evidence:

- `src/configstream/server.py` sets `allow_credentials=True`.
- `src/configstream/config.py` defaults `ALLOWED_ORIGIN_REGEX` to `https://.*\.github\.io`.

Impact:

- Any GitHub Pages subdomain can be treated as a credentialed origin.
- This is broader than a project-specific deployment.
- It expands trust beyond the intended frontend.

Required fix:

1. Remove broad default regex from production.
2. Use explicit origin list for production.
3. Set `allow_credentials=False` unless a specific endpoint requires cookies/credentials.
4. Add CORS tests for allowed and denied origins.
5. Document exact production origin configuration.

Closure checklist:

- Credentialed CORS accepts only intended project origins.
- Security docs match runtime defaults.
- Changelog records the CORS tightening.

Remediation progress:

- `src/configstream/config.py` now defaults `ALLOWED_ORIGIN_REGEX` to empty instead of `https://.*\.github\.io`.
- `src/configstream/config.py` now defaults `CORS_ALLOW_CREDENTIALS` to `False`.
- `src/configstream/server.py` now rejects `ALLOWED_ORIGIN_REGEX` in production startup validation; production must use explicit `ALLOWED_ORIGINS`.
- `.env.example` documents regex CORS as development/test only and adds `CORS_ALLOW_CREDENTIALS=false`.
- `SECURITY.md` now documents explicit-origin CORS and no production wildcard regex.
- `tests/unit/test_server.py` covers default non-credentialed CORS, origin splitting, production regex rejection, and development regex allowance.

Remaining:

- Add HTTP preflight tests if/when the server test harness starts exercising ASGI lifespan and middleware headers directly.

---

### P1-4. WebSocket update endpoint has weak lifecycle control

Evidence:

- `src/configstream/server.py` has an infinite `receive_text()` loop.
- It responds to client `ping`.
- It has no server-side heartbeat, idle timeout, max connection control, bounded outbound queue, or send timeout policy.

Impact:

- Dead or hostile clients can remain in manager state longer than expected.
- Broadcast operations can degrade under connection buildup.
- Hostile networks make stale sockets common.

Required fix:

1. Add server heartbeat.
2. Add idle timeout.
3. Add max connections.
4. Add send timeout and per-client queue cap.
5. Add disconnect cleanup tests.

Closure checklist:

- Stale connections are evicted.
- Broadcast cannot hang on one client.
- Metrics expose active connections and dropped stale connections.
- Changelog records WebSocket lifecycle hardening.

Remediation progress:

- `ConnectionManager` now enforces configurable `WS_MAX_CONNECTIONS`.
- Over-capacity WebSocket clients are closed with code `1013` and counted as dropped.
- `websocket_endpoint()` now applies `WS_IDLE_TIMEOUT_SECONDS` around `receive_text()`.
- Broadcast sends now use `WS_SEND_TIMEOUT_SECONDS`; failed or timed-out clients are evicted.
- `ConnectionManager.stats()` exposes active and dropped connection counts.
- `.env.example` documents WebSocket lifecycle limits.
- `SECURITY.md` documents WebSocket max connection, idle timeout, send timeout, and stale cleanup behavior.
- `tests/unit/test_server.py` covers bounded defaults, over-capacity rejection, failed-send cleanup, and cleanup over a mutation-safe failed-connection snapshot.

Remaining:

- Add a server-originated heartbeat message if clients need active liveness probes beyond timeout-based cleanup.

---

### P1-5. Lab live test endpoint is unauthenticated and resource-heavy

Status: remediated for backend route policy on 2026-05-04. Frontend live/manual labeling remains a follow-up parity polish item.

Evidence:

- `src/configstream/server.py` exposes `POST /api/lab/test-chain`.
- It accepts arbitrary submitted config JSON.
- It calls `test_chain_config(config, timeout=settings.LAB_TEST_TIMEOUT_SECONDS)`.
- `src/configstream/testers/lab_chain_tester.py` can start a sing-box process and run test traffic.
- The route now has production opt-in, admin-key authentication, SlowAPI rate limiting, payload-size enforcement, submitted-config allowlisting, and private/internal destination blocking.

Impact:

- Public deployment could be driven into repeated expensive process/test work.
- Arbitrary submitted configs may contain unsafe routes.
- This conflicts with the no-abuse and no-active-scanning posture unless heavily constrained.

Required fix:

1. Disable this endpoint by default in production.
2. Require explicit `LAB_LIVE_TEST_ENABLED=true`.
3. Add auth or signed one-time tokens for live tests.
4. Add rate limits and payload size limits.
5. Validate submitted configs against a strict allowlist.
6. Block private/internal destinations unless explicitly local-only.
7. Prefer static/manual fallback on GitHub Pages.

Implemented so far:

- `AppSettings.LAB_LIVE_TEST_ENABLED` defaults to `False`.
- Production requests receive `403` unless live testing is explicitly enabled.
- Production-enabled requests must include a matching `api_key` payload field backed by `ADMIN_API_KEY`.
- The endpoint is registered with a `30/minute` rate limit.
- Submitted `config` payloads must be JSON-serializable and no larger than `LAB_MAX_CONFIG_BYTES`.
- Submitted configs must be JSON objects with a non-empty `outbounds` array.
- Outbound types are limited to known low-level proxy/direct/block types needed by the lab.
- Outbound `server` and `address` fields reject localhost, internal suffixes, invalid host syntax, and private/non-global IP literals.
- The chain-test timeout is configurable through `LAB_TEST_TIMEOUT_SECONDS`.
- Nonproduction `development`, `ci`, and `test` flows remain compatible for local testing.
- `.env.example`, `SECURITY.md`, `STATUS.md`, `CHANGELOG.md`, and server tests now document and verify the new policy.

Remaining:

- Add frontend copy/state that makes live-vs-manual test mode visible without implying GitHub Pages can run server-side tests.

Closure checklist:

- Public static deployment cannot spawn tester work.
- Local live server can opt in safely.
- Frontend clearly distinguishes static manual testing from live API testing.
- Changelog records endpoint policy.
- After each additional change, verify backend, frontend, docs, schema/config, tests, and changelog parity, then remove any stale legacy/deprecated statements instead of keeping backward-compatibility clutter.

---

### P1-6. Fetcher SSRF and redirect safety are incomplete

Status: partially remediated on 2026-05-04. Literal private/internal targets and unsafe redirects are blocked; DNS-resolution/rebinding validation remains a follow-up hardening item.

Evidence:

- `src/configstream/fetcher.py` now parses source URLs structurally.
- Fetching no longer delegates redirect following to `httpx`; redirects are followed manually after target validation.
- `src/configstream/http_client.py` applies cached DNS safety only to HTTP requests and explicitly lets HTTPS use the standard resolver.
- `ALLOW_PRIVATE_IPS` defaults to `True`.

Impact:

- Source URLs or redirects can resolve to unexpected private/internal addresses.
- HTTPS redirects are not post-resolution-filtered by the custom DNS cache path.
- A hostile source list can test boundaries around internal network access.

Implemented so far:

- `FETCH_BLOCK_PRIVATE_NETWORKS=true` blocks private/non-global IP literals by default for source URLs and redirect targets.
- Source URLs with embedded credentials are rejected.
- `localhost`, `.localhost`, `.local`, `.lan`, and `.internal` hostnames are rejected.
- Redirects are validated one hop at a time through structured URL parsing.
- Redirect depth is capped by `FETCH_MAX_REDIRECTS`.
- Tests cover direct private source URLs, safe redirects, private redirect targets, and redirect-depth limits.
- `.env.example`, `SECURITY.md`, `STATUS.md`, `CHANGELOG.md`, and this audit report now describe the fetch policy.

Required fix:

1. Canonicalize source URLs with structured parsing.
2. Resolve and validate each final target after redirects.
3. Block private, loopback, link-local, multicast, and special-use ranges by default for fetch sources.
4. Add explicit local/test override only.
5. Add SSRF tests for direct private URL, DNS rebinding style hostname, redirect to private IP, and HTTPS redirect.

Remaining:

- Add async DNS resolution validation for hostname targets before connection, including HTTPS, without blocking the event loop.
- Re-validate resolved addresses after each redirect target is chosen.
- Add DNS rebinding-style hostname tests by injecting a resolver abstraction.
- Decide whether the existing proxy-validation `ALLOW_PRIVATE_IPS` default should remain separate from fetch-source safety or be renamed/documented to avoid confusion.

Closure checklist:

- Fetcher blocks private/internal fetch targets by default.
- Redirect target validation is tested.
- Docs describe allowed source URL policy.
- Changelog records fetcher security hardening.
- After each additional fetch hardening change, verify backend tests, pipeline behavior, config docs, security docs, status, changelog, and remove stale redirect/SSRF claims instead of preserving backward-compatible ambiguity.

---

### P1-7. Frontend key injection and verification are split-brain

Status: partially remediated on 2026-05-04. Pages deploy now injects and validates frontend placeholders; the larger Vite-vs-raw-frontend production-build decision remains open.

Evidence:

- `frontend/assets/js/constants.js` contains placeholder `PUBLIC_KEY`.
- `frontend/assets/js/stego.js` contains `PLACEHOLDER_KEY_INJECTED_BY_CI`.
- `src/configstream/output_handler.py` can inject a stego key into the local frontend tree.
- `.github/workflows/main.yml` uploads only `output/` as the pipeline artifact.
- `.github/workflows/deploy-pages.yml` checks out the repo and copies raw `frontend/.` into `output/`.
- `vite.config.mjs` builds to `frontend-dist`, but deploy does not use it.
- `frontend/assets/js/verifier.js` skips verification when public key is not configured.

Impact:

- Production Pages likely serves placeholder key material.
- CI secrets passed as env vars do not necessarily affect deployed frontend files.
- Signature verification is advertised but can silently skip.
- Stego assets and frontend code can diverge.

Implemented so far:

- Added `scripts/validate_frontend_placeholders.py`.
- Pages deploy runs `python scripts/validate_frontend_placeholders.py --inject-env --strict output` after copying frontend assets and before refreshing the public artifact contract.
- Pages deploy now passes `CS_PUBLIC_KEY` and `STEGO_KEY` into the frontend placeholder guard step from GitHub secrets.
- The validator replaces `assets/js/constants.js` `PUBLIC_KEY` from `CS_PUBLIC_KEY` when provided.
- The validator replaces `assets/js/stego.js` `SECRET_KEY` from `STEGO_KEY` or `CONFIG_STREAM_KEY` when provided.
- The validator fails if the public key placeholder marker or stego placeholder remains in the Pages artifact.
- `scripts/validate_workflows.py` now requires the Pages frontend placeholder guard and secret env wiring.
- Tests cover placeholder detection, env injection, optional non-strict stego handling, and workflow guard retention.

Required fix:

1. Choose one frontend production build path.
2. Use generated build artifacts, not raw `frontend/`, for Pages.
3. Inject keys at build time into a generated config file.
4. Fail production build if required public key/stego key placeholders remain.
5. Fail closed on signature verification for signed artifacts.
6. Add placeholder leak tests.

Remaining:

- Decide and implement the canonical production frontend path: tested Vite build output or deliberately raw static output, not both.
- Move frontend runtime keys into a generated config artifact rather than editing source-shaped JS in the deploy artifact.
- Make `verifier.js` fail closed for signed artifacts when public key material is unavailable or WebCrypto is unsupported.
- Add browser/deploy-smoke coverage proving the deployed frontend uses the same assets that CI tested.

Closure checklist:

- Deployed frontend contains no placeholder key strings.
- Public-key source is documented and tested.
- Production deploy uses the same build output tested by CI.
- Changelog records frontend build/injection contract.
- After each frontend contract change, verify backend output, deploy workflow, frontend files, tests, README/wiki/security/status/changelog, and delete stale placeholder/build-path language completely.

---

### P1-8. Public schemas, runtime outputs, docs, and deployed artifacts disagree

Status: partially remediated on 2026-05-04. Pages validation now enforces tighter schema/key checks and API alias parity; README now describes the canonical `proxies.json` array contract. Snapshot identity and full schema/deploy smoke coverage remain open.

Examples:

- `README.md` previously said `proxies.json` was a full dataset with metadata; it now states `proxies.json` is a JSON array and `metadata.json` owns run statistics.
- `src/configstream/output_handler.py` says `proxies.json` must be a JSON array.
- `docs/wiki/project/08-api-reference.md` now describes `proxies.json` as array items.
- `schema/metadata.schema.json` requires fields missing from live public metadata.
- `/api/diff/proxies` accepts a `base_version` string but does not verify it matches a specific persisted old snapshot identity.

Impact:

- Frontend, external tooling, and docs cannot rely on a single contract.
- Diff updates may be semantically wrong even when syntactically valid.
- API consumers cannot tell which shape is canonical.

Implemented so far:

- `scripts/validate_pages_artifact.py` now rejects unknown top-level keys for control-file schemas that declare `additionalProperties: false`.
- Pages validation now checks that `api/proxies` is byte-equivalent to `proxies.json`.
- Pages validation now checks that `api/stats` is byte-equivalent to `metadata.json`.
- README now separates `proxies.json` as the canonical proxy array from `metadata.json` as the canonical statistics object.
- Documentation hygiene tests prevent reintroducing the stale “proxies.json with metadata” envelope claim.
- Artifact validation tests cover unknown metadata keys and API alias drift.

Required fix:

1. Decide canonical public shapes:
   - `proxies.json`: array or envelope, not both.
   - `metadata.json`: schema-required fields must match generated output.
2. Update schema, generator, server, frontend, README, wiki, tests, and examples together.
3. Delete transitional references to the rejected shape.
4. Version snapshots with hashes/ETags, not only `base_version` strings.
5. Add contract tests that load generated artifacts and validate schemas.

Remaining:

- Validate nested schema semantics more fully, either with a zero-budget vendored/minimal validator or by constraining the schemas to checks the local validator enforces.
- Add generated-output contract tests that run the output writer and validate the produced artifact, not only hand-built fixtures.
- Add snapshot identity/hashing for `/api/diff/proxies` so `base_version` cannot refer to an ambiguous old list.
- Re-scan README and wiki examples after every output-contract change and delete stale envelope examples completely.

Closure checklist:

- One canonical contract exists.
- No docs mention rejected shape.
- No server route assumes a different shape.
- Public artifact validates against schema.
- Changelog records breaking schema cleanup.
- After each public-contract change, verify generator, server aliases, frontend fetchers, schemas, deploy artifact validation, docs, changelog, and cleanup of old rejected shapes in one pass.

---

## 7. P2 Findings

### P2-1. Lab strategy list is inconsistent and partially broken

Status: partially remediated on 2026-05-04. The UI, JS hints/build paths, README, wiki, and a canonical strategy manifest now agree on 9 strategies; browser-level strategy tests remain a follow-up.

Evidence:

- `frontend/lab.html` lists 9 strategies:
  - `warp`
  - `vwarp-masque`
  - `vwarp-atomic`
  - `warp-in-warp`
  - `warp-psiphon`
  - `relay-chain`
  - `fragment`
  - `worker`
  - `custom`
- `frontend/assets/js/lab.js` `CHAIN_HINTS` omits `vwarp-masque` and `vwarp-atomic`.
- `handleStep3Next()` has no branches for those two values.
- The function can continue to show success and proceed even when no new `chainConfig` was built for those selections.
- Docs mention 5, 6, 7, and 9 strategies depending on file.

Impact:

- Users can select a strategy that does not generate the intended config.
- Docs and UI disagree.
- Vwarp feature claims are not reliably wired into the lab.

Implemented so far:

- Added `frontend/assets/data/lab_strategies.json` as the canonical 9-strategy manifest.
- Added JS hints for `vwarp-masque` and `vwarp-atomic`.
- Added build branches for `vwarp-masque` and `vwarp-atomic`; both build the standard WARP chain and attach `_vwarp` metadata plus CLI hints.
- Added a fail-loud unsupported-strategy branch so unknown selections cannot silently advance with stale config.
- Updated Lab copy to describe TLS Fragment as legacy/manual because native sing-box fragmentation remains disabled.
- Updated README and frontend wiki to the same 9-strategy count.
- Added `tests/unit/test_lab_strategy_parity.py` to verify manifest, HTML options, JS hints, and docs count stay aligned.

Required fix:

1. Create canonical `lab_strategies.json`.
2. Generate HTML options, JS handling, docs tables, and tests from the canonical list.
3. Implement or remove `vwarp-masque` and `vwarp-atomic`.
4. Fail loudly if a selected strategy has no builder.
5. Add UI tests for every strategy.

Remaining:

- Move the HTML options and JS hints to generated or runtime-loaded data from `lab_strategies.json` instead of maintaining parallel literals.
- Add browser tests that exercise every strategy through the actual Lab UI.
- Add export assertions for Vwarp metadata in Sing-box/Clash/Xray/manual outputs.

Closure checklist:

- Every strategy has docs, UI option, JS handler, export behavior, and test coverage.
- Strategy count is identical in README, STATUS, wiki, AGENTS, and UI.
- Changelog records lab strategy cleanup.
- After each Lab strategy change, verify frontend, export behavior, docs, tests, changelog, and delete stale strategy-count wording instead of preserving legacy counts.

---

### P2-2. Lab QR generation leaks user config to an external service

Status: remediated for the third-party leak; follow-up remains for a scannable local QR renderer.

Previous evidence:

- `frontend/assets/js/lab.js` builds an image URL to `https://api.qrserver.com/v1/create-qr-code/` and passes the encoded proxy/chain payload as a query parameter.

Implemented remediation:

- `generateQR()` no longer builds an external image URL.
- The Lab now renders an offline payload panel directly in the browser using DOM nodes and a copy button.
- Exported QR payload material no longer leaves the page for `api.qrserver.com` or any other QR endpoint.
- `tests/unit/test_lab_strategy_parity.py` asserts that the external QR service strings are absent and that the offline QR copy path is present.

Residual work:

1. Add a small audited offline QR renderer if the UX must show a scannable matrix instead of a copyable payload.
2. Keep the QR implementation dependency-free or vendored/free so it stays compatible with zero-budget/offline constraints.
3. Add browser-level tests proving no network request is made while exporting the QR payload.

Closure checklist:

- Done: no proxy payload is sent to third-party QR endpoints.
- Done: Lab QR export works offline as a local copyable payload.
- Done: changelog records privacy cleanup.
- Remaining: optional scannable offline QR matrix and browser-level network assertion.

---

### P2-3. Lab manual clean IP table can inject HTML

Status: partially remediated; the manual clean-IP table path is fixed, while broader `showResult()` hardening remains open.

Previous evidence:

- `frontend/assets/js/lab.js` renders manual IP entries with `tr.innerHTML`.
- The `ip.ip` value can originate from user input.
- `showResult()` also uses `innerHTML` for messages, including some error flows.

Implemented remediation:

- Manual clean-IP rows now use `tbody.replaceChildren()`, explicit `td` creation, and `textContent`.
- Manual clean-IP input is parsed through `parseManualCleanIpLine()` and accepts only hostnames, IPv4-style host strings, or bracketed IPv6 with optional valid port.
- Invalid manual entries fail before storage with a clear message.
- `tests/unit/test_lab_strategy_parity.py` asserts that the table renderer uses text nodes and no longer contains `tr.innerHTML`.

Remaining required fix:

1. Split `showResult()` into explicit safe-text and trusted-template helpers.
2. Convert user-controlled success/error paths, including custom JSON parse errors and live-test errors, to text-node rendering.
3. Add browser-level XSS tests for manual clean IP input, custom JSON errors, live-test errors, and parsed proxy remarks.
4. Keep icon-only trusted templates separate from user data and document the trusted-template allowlist.

Closure checklist:

- Done: manual clean-IP input no longer enters `innerHTML`.
- Done: manual clean-IP table regression test passes.
- Remaining: global Lab `showResult()` sanitization pass and browser XSS coverage.
- Changelog records frontend sanitization cleanup.

---

### P2-4. Async routes still perform blocking filesystem reads

Status: remediated for direct blocking JSON reads in the affected routes; cache/performance load testing remains a follow-up.

Previous evidence:

- `server.py` `get_proxy_diff()` calls `Path.read_text()` inside an async route.
- `server.py` `get_stats()` calls `Path.read_text()` inside an async route.

Implemented remediation:

- `src/configstream/server.py` now centralizes JSON artifact loading in `_read_json_file()`.
- Async route handlers call `_read_json_file_async()`, which uses `asyncio.to_thread()` so disk reads and JSON parsing happen outside the event loop.
- `/api/stats` now reads `metadata.json` off the event loop.
- `/api/diff/proxies` now reads both `proxies.json` and `proxies.old.json` off the event loop.
- `tests/unit/test_server.py` verifies both routes dispatch artifact reads through `asyncio.to_thread()`.

Remaining work:

1. Add parsed-artifact caching with invalidation based on file mtime/hash if route load becomes significant.
2. Add a concurrent large-file route test or benchmark to quantify latency under heavy artifact size.
3. Revisit `/api/diff/proxies` snapshot identity so diff reads are both nonblocking and semantically tied to a specific artifact version.

Closure checklist:

- Done: affected async route handlers no longer perform direct blocking disk reads for JSON artifacts.
- Done: route-level regression tests cover off-event-loop dispatch.
- Changelog records async I/O cleanup.

---

### P2-5. Test budget semaphore is initialized but unused

Status: remediated by deleting the unused semaphore wiring and retaining `ConcurrencyManager` as the canonical test limiter.

Previous evidence:

- `src/configstream/pipeline.py` initializes `test_budget: Optional[asyncio.Semaphore] = None`.
- It passes the value into `processing_consumer`.
- `src/configstream/consumer.py` accepts `test_budget`.
- The consumer body does not use it for Go batch testing.

Implemented remediation:

- Removed the unused `test_budget` local from `src/configstream/pipeline.py`.
- Removed the unused `test_budget` argument from the `processing_consumer()` call.
- Removed the unused `test_budget` parameter from `src/configstream/consumer.py`.
- Kept Python fallback testing under `ConcurrencyManager.get_semaphore()`, which is already the active limiter.
- Added `tests/unit/test_concurrency_contract.py` to prevent reintroducing `test_budget` and to assert that the consumer still uses `ConcurrencyManager` for Python test concurrency.

Remaining work:

1. Add deeper integration tests for Go batch daemon pressure if a future change adds multi-daemon or per-host limiter behavior.
2. Keep revival retests under review because Vwarp/WARP batch tests still rely on the Go tester's own batch/timeout protections.

Closure checklist:

- Done: `ConcurrencyManager` remains the single Python fallback test-concurrency owner.
- Done: no unused `test_budget` semaphore parameters remain.
- Done: contract tests prevent reintroducing the dead wiring.
- Changelog records concurrency model cleanup.

---

### P2-6. Source-quality accounting can punish sources for queue pressure

Status: remediated for the producer zero-queued backpressure path.

Previous evidence:

- `producer.py` records `backpressure_drop`.
- When the queue is pressured and no chunks are queued, source failure can be reported as `backpressure_drop`.

Implemented remediation:

- Added `_report_source_backpressure()` in `src/configstream/producer.py`.
- Local-file and remote-source zero-queued backpressure paths now record a run with `failure_modes_json={"backpressure_drop": ...}` without calling `SourceQualityTracker.report_failure()`.
- Pipeline stats still receive backpressure counts through the existing `_record_backpressure_drop()` path.
- `tests/unit/test_producer_quality_accounting.py` verifies backpressure accounting does not increment source failure state.

Remaining work:

1. Add an end-to-end overloaded bounded-queue producer test if the producer sentinel path is refactored to make that scenario easy to isolate.
2. Consider exposing backpressure pressure/keep-ratio snapshots in metadata so operators can distinguish source poverty from runner capacity pressure.

Closure checklist:

- Done: backpressure is no longer treated as remote source unreliability in the zero-queued producer path.
- Done: pipeline capacity metrics still record backpressure drops.
- Done: changelog records source-quality metric cleanup.

---

### P2-7. Unsanitized or partially sanitized logging remains

Status: substantially remediated. Converter hot paths, batch DNS failure logs, Vwarp subprocess-output/tunnel failure logs, security rule address logs, honeypot passive-intel logs, test-cache endpoint logs, and parser drop/error logs now sanitize sensitive text with regression coverage. High-risk static enforcement and security-doc policy are in place; broader full-repository f-string/log-call debt outside these high-risk surfaces remains a follow-up.

Examples found by targeted scan have been remediated in the affected converter, DNS, Vwarp, security, cache, and parser paths. The remaining risk is lower-priority log-call drift in modules outside the high-risk proxy/config handling surfaces.

Impact:

- Logs can contain proxy endpoints, credentials, UUIDs, hostnames, or config fragments.
- This conflicts with the project rule that sensitive logs must be sanitized.

Required fix:

1. Create a logging policy test that flags sensitive arguments not passed through `SecurityValidator.sanitize_log_message`.
2. Sanitize endpoints, URLs, UUIDs, passwords, keys, tokens, and raw config snippets.
3. Use structured logging fields only after masking.
4. Add tests for representative log messages.

Closure checklist:

- Sensitive log scan passes.
- New logger policy is documented.
- Changelog records log sanitization hardening.

Implemented so far:

- `src/configstream/converters/common.py` now sanitizes proxy address and exception text before URI reconstruction failure logs.
- `src/configstream/converters/singbox.py` now uses `_safe_proxy_ref()` and `_safe_source_ref()` for key drop/conversion logs that previously interpolated `proxy.address`, `proxy.port`, source URLs, or plugin values directly.
- `src/configstream/dns_batch_resolver.py` now sanitizes both hostname and exception text before debug logging DNS resolution failures.
- `src/configstream/tools/vwarp.py` now routes Vwarp version-check errors, install/config write errors, scan exceptions, tunnel stdout/stderr, port-check exceptions, background process lines, and stored `_last_failure_details` through `_sanitize_process_output()`, which decodes safely, masks sensitive material, and bounds log length.
- `src/configstream/security/rules.py` now sanitizes address/error values in security-rule warning/debug logs.
- `src/configstream/security/honeypot.py` now sanitizes host and exception values in passive reputation logs.
- `src/configstream/test_cache.py` now sanitizes proxy endpoint references in cache hit/miss logs.
- Parser modules now sanitize parse exceptions, invalid host/port values, WireGuard key diagnostics, OpenVPN host/transport failures, SSR/Shadowsocks/VMess/Trojan failures, and extraction drop samples. Extraction no longer logs raw dropped-line snippets.
- `tests/unit/test_logging_sanitization_policy.py` verifies that converter, DNS, Vwarp, security-rule, honeypot, test-cache, Shadowsocks, OpenVPN, and extraction logs mask representative endpoint/token/config material.
- `tests/unit/test_logging_sanitization_policy.py` also includes an AST/static policy guard for high-risk logging surfaces. It rejects sensitive f-string interpolation, `%` or `.format()` logger messages, and raw sensitive logger arguments unless they use the approved sanitizer wrappers.
- `SECURITY.md` now documents the logging policy, approved sanitizer wrappers, high-risk module coverage, dropped-line marker behavior, and Vwarp subprocess-output bounds.

Remaining:

1. Extend static logging policy beyond the high-risk surfaces once the older full-repository f-string logger debt is burned down.
2. Keep the parser/converter/security log scan in the validation checklist so future protocol additions do not reintroduce raw config snippets.

---

### P2-8. Frontend still depends on remote CDNs and remote assets

Status: Remediated in this checkpoint. Primary production pages now load
critical scripts, styles, fonts, globe textures, country flags, and Lab helper
downloads from same-origin assets; runtime CDN hosts are covered by static and
browser same-origin-only regression tests. Localized assets preserve the online
experience, with reduced offline fallbacks kept separate from the main path;
`frontend/assets/vendor-manifest.json` records the mirrored sources.

Validation: `npm run build`, `npm run test:frontend:no-network`,
`tests/unit/test_frontend_local_first.py`, workflow and documentation hygiene
tests passed locally. The Python Playwright e2e file still records the
environment skip when its browser bundle is unavailable; P2-9 tracks making
browser execution non-optional in CI.

Examples:

- `unpkg.com` for Feather, Three, Globe images.
- `cdn.jsdelivr.net` for Chart, fonts, Bootstrap in worker UI.
- `cdnjs.cloudflare.com` for pako and highlight assets.
- `flagcdn.com` for country flags.
- `raw.githubusercontent.com` for wiki/lab downloads.
- `api.qrserver.com` for QR generation.

Impact:

- Restricted networks can block critical frontend behavior.
- CSP allows several remote hosts.
- Self-hosted fallback exists for some libraries but not every remote dependency.

Required fix:

1. Make production frontend local-first.
2. Self-host all critical JS/CSS/image assets.
3. Treat remote URLs as optional links, not runtime dependencies.
4. Add a no-network frontend smoke test.
5. Tighten CSP after self-hosting.

Closure checklist:

- [x] Frontend usable with network blocked except same-origin.
- [x] CSP no longer needs broad external runtime dependencies.
- [x] Changelog records frontend dependency cleanup.

---

### P2-9. E2E browser tests are easy to skip

Status: Remediated in this checkpoint. Test profiles now split unit,
integration, frontend-browser, and production-smoke runs; the frontend-browser
profile fails loudly when Python Playwright browsers are required but missing.
CI has a dedicated required frontend-browser job, and Node Playwright smokes
cover same-origin and no-JS degraded frontend loading.

Evidence:

- `tests/e2e/test_frontend.py` applies `pytest.mark.skipif` when Playwright browsers are not installed.
- Local full test pass had 4 skipped tests.
- CI intends to install Playwright, but workflow YAML is currently invalid.

Impact:

- Local "all tests passed" can hide missing browser validation.
- Frontend/lab regressions can escape.

Required fix:

1. Split test profiles:
   - unit
   - integration
   - frontend-browser
   - production-smoke
2. Make browser tests required in CI after workflow repair.
3. Make skip status visible in `STATUS.md`.
4. Add no-JS/degraded frontend tests.

Closure checklist:

- [x] Browser tests are required by CI configuration.
- [x] Local skipped-browser result is clearly labeled.
- [x] Changelog records testing profile cleanup.

---

### P2-10. `scripts/validate_versions.py` is not Windows-safe

Status: Remediated in this checkpoint. The script now uses explicit UTF-8
file reads and ASCII-only status/error output, and a regression test simulates
Windows cp1252 console semantics while reading a UTF-8 changelog entry.

Evidence:

- Running the script on Windows with default console encoding fails on emoji output.
- With `PYTHONIOENCODING=utf-8`, it still fails reading `CHANGELOG.md` because `read_text()` has no explicit encoding and falls back to cp1252.

Impact:

- A governance script fails on a contributor platform.
- Cross-platform readiness is overstated.

Required fix:

1. Add explicit `encoding="utf-8"` to file reads.
2. Avoid emoji output in scripts or configure safe output.
3. Add Windows CI or at least script-level tests under Windows semantics.

Closure checklist:

- [x] `validate_versions.py` passes on Windows and Linux.
- [x] Changelog records cross-platform script fix.

Validation: `python scripts/validate_versions.py` passed through the
`production-smoke` profile, and `python -m pytest
tests/unit/test_validate_versions.py -q` passed with coverage for UTF-8 file
reads under strict cp1252 stdout semantics.

---

### P2-11. Rust Shadowsocks FFI fallback and checksum story are incomplete

Status: Remediated in this checkpoint. The Rust Shadowsocks FFI checker is
explicitly optional, is not counted as a production security guarantee, and is
enabled only when a local platform binary exists and `SS_LIB_SHA256` is
configured. Missing binaries and unset hashes skip the FFI path while preserving
Python validation; configured hash mismatches fail closed.

Evidence:

- `ss_ffi.py` has a hardcoded example hash unless `SS_LIB_SHA256` is set.
- If the library is absent, enhanced validation is skipped and returns `True`.
- If the library is present but does not match the placeholder hash, validation fails.

Impact:

- The feature is either absent, fail-open, or likely fail-closed depending on binary presence and env.
- Docs should not imply strong Rust validation unless binary distribution and hash management are real.

Required fix:

1. Decide whether Rust FFI is production-supported.
2. If supported, provide verified binaries or documented build step and real hashes.
3. If optional, label it as optional and do not count it as a security guarantee.
4. Add tests for missing library, bad hash, good hash, and invalid SS config.

Closure checklist:

- [x] Rust validation behavior is deterministic and documented.
- [x] Changelog records FFI support decision.

Validation: `python -m pytest tests/unit/test_ss_ffi.py -q` passed with
coverage for missing library, present library without configured hash, bad hash,
good hash, invalid config, ctypes loading errors, and FFI exceptions.

---

### P2-12. WASM tester is browser-constrained and should not be described as native network testing

Status: Remediated in this checkpoint. WASM/browser verification is now
documented and labeled as browser-limited reachability only. The frontend keeps
sidecar/Python results authoritative for unsupported transports, and the Go WASM
path reports unsupported schemes and invalid URLs explicitly before creating a
browser `WebSocket`.

Evidence:

- `src/go/tester/wasm_main.go` uses `syscall/js`.
- It creates browser `WebSocket` objects from transformed proxy URLs.
- It cannot perform native proxy networking in the browser sandbox.

Impact:

- Browser verification is not equivalent to Go sidecar testing.
- Docs must clearly state what the WASM tester can and cannot prove.

Required fix:

1. Document WASM tester as browser reachability/interop only.
2. Add UI labels that distinguish browser-limited checks from sidecar tests.
3. Add tests for unsupported schemes and invalid URL recovery.

Closure checklist:

- [x] Docs stop overclaiming WASM test strength.
- [x] Changelog records WASM semantics cleanup.

Validation: `python -m pytest tests/unit/test_wasm_browser_semantics.py
tests/unit/test_documentation_hygiene.py -q` passed with checks for
browser-limited labels, unsupported/invalid URL handling, and documentation
wording.

---

## 8. P3 Findings

### P3-1. Documentation status is stale and overconfident

Status: Remediated for the primary status page in this checkpoint.
`STATUS.md` is now checked by `scripts/validate_status.py`, and the
`production-smoke` profile runs that validator before frontend build/smoke
checks. Secondary docs cleanup remains an ongoing P3 track.

Examples:

- `STATUS.md` claims latest full run `811 passed, 3 skipped`, but current local result after dev setup was `823 passed, 4 skipped`.
- `STATUS.md` claims all workflows green, but five workflows do not parse.
- `STATUS.md` and `CHANGELOG.md` claim zero TODO/FIXME despite generated debt matrices listing many markers.
- `pyproject.toml` classifies the project as `Production/Stable`, which is not accurate for the current deployment/CI state.

Required fix:

1. Rewrite `STATUS.md` from executable evidence.
2. Remove unsupported "production ready" claims until P0/P1 are closed.
3. Make `STATUS.md` generated or checked by script.
4. Update changelog after each remediation step.

Remediation progress:

- `STATUS.md` has been rewritten as a remediation status page and no longer claims final production readiness.
- `pyproject.toml` now uses `Development Status :: 4 - Beta` during remediation instead of `Production/Stable`.
- README TLS fragmentation language now matches the implementation state: disabled in current sing-box outputs.
- `tests/unit/test_documentation_hygiene.py` now guards against reintroducing the stale Production/Stable and active TLS-fragmentation claims.

Remaining:

- Done for primary status: `scripts/validate_status.py` checks remediation
  posture, source-of-truth linkage, browser-skip visibility, full pytest
  snapshot shape, and Beta classifier parity.
- Continue removing stale readiness/metric claims from secondary docs and generated documentation.

Validation: `python scripts/validate_status.py` and `python -m pytest
tests/unit/test_validate_status.py tests/unit/test_documentation_hygiene.py -q`
passed locally.

---

### P3-2. Duplicate docs trees drift

Status: Remediated in this checkpoint. `docs/wiki/encyclopedia` is canonical
because it is the path referenced by the wiki index and frontend wiki flow.
`docs/encyclopedia` has been synced as a byte-identical mirror, and
`scripts/validate_docs_sync.py` now fails on missing, extra, or drifted mirror
files.

Evidence:

- `docs/encyclopedia/...` and `docs/wiki/encyclopedia/...` contain matching topic paths but different content and different lengths.
- 12 paired encyclopedia files differ.

Impact:

- Two documentation truths exist.
- Updates can land in one tree and not the other.

Required fix:

1. Done: `docs/wiki/encyclopedia` is canonical.
2. Done: `docs/encyclopedia` is treated as a generated/synced mirror.
3. Done for current drift: all 12 mirrored files are byte-identical.
4. Done: `scripts/validate_docs_sync.py` and
   `tests/unit/test_validate_docs_sync.py` guard mirror parity.

Validation: `python scripts/validate_docs_sync.py` and `python -m pytest
tests/unit/test_validate_docs_sync.py -q` passed locally.

---

### P3-3. Debt matrix artifacts contain machine-local absolute paths and self-reference

Status: Remediated in this checkpoint. `scripts/generate_debt_matrix.py` now
scans tracked text files, emits repo-relative POSIX paths, excludes generated
debt artifacts and generated/mirrored/vendor trees, classifies entries by
surface (`production`, `test`, `frontend`, `docs`, `ci`, `tooling`, `other`),
and regenerates portable `docs/DEBT_MATRIX.md` / `docs/debt_matrix.json`.
`scripts/validate_debt_matrix.py` now fails on absolute paths, backslash paths,
generated-artifact self-reference, and missing category summaries.

Evidence:

- `docs/DEBT_MATRIX.md` and `docs/debt_matrix.json` contain thousands of `D:/GitHub/ConfigStream/...` references.
- The debt matrix includes entries about itself, causing self-amplifying noise.

Impact:

- The artifact is not portable.
- The governance signal is noisy.
- Windows/local path details leak into repo docs.

Required fix:

1. Done: generated paths are repo-relative POSIX paths only.
2. Done: `docs/DEBT_MATRIX.md` and `docs/debt_matrix.json` are excluded from
   scans.
3. Done: entries include a `category` field and summaries separate test-only
   mocks from production/frontend/tooling/docs debt.
4. Done: artifacts regenerated on 2026-05-07; marker count reduced from 5,411
   noisy absolute/self-referential entries to 1,402 portable categorized
   entries.

Validation: `python scripts/validate_debt_matrix.py` and `python -m pytest
tests/unit/test_debt_matrix.py -q` passed locally.

---

### P3-4. Zero-byte and placeholder assets remain

Observed zero-byte tracked files:

- `.nojekyll` - expected
- `src/configstream/py.typed` - expected marker

Required fix:

1. Done: intentional marker files are allowlisted by `scripts/validate_assets.py`.
2. Done: unused zero-byte `frontend/assets/images/header-bg.png` was deleted.
3. Done: unreferenced root `NL` and `US` placeholder files were removed.
4. Done: tracked concrete frontend image references are checked for existence and
   non-empty files; dynamic template refs are ignored, and broken optional PWA
   screenshot entries were removed from `frontend/manifest.json`.

Validation: `python scripts/validate_assets.py` and `python -m pytest
tests/unit/test_validate_assets.py -q` passed locally.

---

### P3-5. Optional external publishing scripts blur the zero-budget core

Evidence:

- Workflow and scripts include optional Pinata/IPFS, Hugging Face, Google Drive, and Telegram upload paths.
- These are conditional on secrets, but docs sometimes present mirrors as part of the project capability.

Impact:

- Zero-budget core can be confused with optional external accounts/services.
- Security and privacy posture becomes harder to audit.

Required fix:

1. Done for publishing docs: GitHub Pages is classified as the core
   zero-budget publication target.
2. Done for publishing docs: IPFS/Pinata, Hugging Face, Google Drive, and
   Telegram publishing paths are classified as optional, secret-gated mirrors.
3. Done: introduction, architecture, DevOps, and configuration docs now state
   optional mirrors are not required for core success.
4. Done: `scripts/validate_optional_mirrors.py` is wired into
   `production-smoke` and blocks stale always-on mirror claims.

Validation: `python scripts/validate_optional_mirrors.py` and `python -m pytest
tests/unit/test_validate_optional_mirrors.py -q` passed locally.

---

## 9. Confirmed Good / Partially Healthy Areas

These items were verified as aligned with current project rules or at least materially improved:

- Removed legacy files listed in AGENTS are absent:
  - `pipeline_stages.py`
  - `dns_prewarm.py`
  - `quality/geo.py`
  - `intelligence/washer.py`
  - `tools/vwarp_tool.py`
  - `fetcher_core/`
  - `pipeline_core/`
  - `output.py`
  - `crypto/`
  - `transport/`
  - `workers/`
- `BlocklistManager` and `GeoIPResolver` use locked singleton construction.
- `pipeline.py` updates `DEFAULT_BLOCKLIST` before processing.
- `pipeline.py` closes anomaly detector during shutdown.
- `generators/split.py` caches base outbound generation and deep-copies for Sniper/Tank.
- `tools/vwarp.py` is canonical and includes `VwarpTool.validate_warp_key`.
- Vwarp constants are centralized.
- Vwarp scan timeout is 60 seconds.
- Washer WireGuard outbounds include `mtu: 1280`.
- Go tester supports JSON array chain payloads.
- Go batch tester tracks consecutive timeouts, disables after 5, and awaits restart.
- VLESS, Trojan, and Shadowsocks parser credential fallback behavior is present.
- Shadowsocks invalid method handling exists.
- DNS cache passthrough into output generation exists.
- Chosen output fallback from working to all proxies exists.
- Country/protocol categorized outputs preserve all proxies.
- `flake8`, `black --check`, and `mypy` pass locally.

These positives do not cancel the P0/P1 blockers, but they matter: the codebase has real structure worth stabilizing.

---

## 10. Module-By-Module Audit Summary

### 10.1 `.github/workflows`

State:

- Critical syntax failure in 5 workflows.
- Broad permissions in `main.yml`.
- Root container execution in `main.yml`.
- Self-trigger risk via source optimization commits.
- Deploy copies raw frontend and fails closed on sparse outputs.

Next action:

- Fix syntax first.
- Add actionlint.
- Redesign pipeline/deploy/reshard separation.

### 10.2 Root config and package metadata

State:

- `pyproject.toml` says Production/Stable.
- `package-lock.json` resolves vulnerable Vite/picomatch/postcss versions.
- `requirements.txt` and `requirements-prod.txt` pin yanked `numpy==2.4.0`.
- `validate_versions.py` is not Windows-safe.

Next action:

- Make metadata truthful.
- Update vulnerable/yanked dependencies.
- Add cross-platform script checks.

### 10.3 Fetcher and HTTP client

State:

- Adaptive timeout and circuit breaker concepts exist.
- Binary-safe streaming exists.
- SSRF and redirect post-resolution filtering are incomplete.

Next action:

- Add strict source URL and redirect target validation.

### 10.4 Producer/consumer/pipeline

State:

- Bounded queue exists.
- Backpressure tracking exists.
- Soft time limit exists.
- Global test budget parameter appears unused.
- Source-quality backpressure semantics need separation.

Next action:

- Define one concurrency/backpressure authority.
- Ensure source quality reflects source behavior, not runner overload.

### 10.5 Parsers

State:

- Robust credential fallback exists for key protocols.
- Extraction returns configs plus drop stats.
- Some log statements may expose snippets or endpoints.

Next action:

- Add parser log-sanitization tests.
- Keep malformed-input fuzz tests.

### 10.6 Testers

State:

- Go tester has important resilience features.
- Python fallback exists.
- Lab live test endpoint policy is too open.
- WASM tester is browser-limited.

Next action:

- Separate sidecar test, Python fallback test, browser reachability test, and live lab test semantics.

### 10.7 Washer/WARP/Vwarp

State:

- Canonical washer and Vwarp classes are in place.
- WARP MTU invariant is present.
- Shielded candidate accounting is wrong.

Next action:

- Separate candidate generation from verified revival.

### 10.8 Output generation

State:

- Many outputs are generated.
- DNS-safe/hardened pass-through exists.
- Chosen fallback exists.
- Metadata accounting has critical shielded-count inflation.
- Public artifact manifest is missing.

Next action:

- Define output contracts with schemas and manifest.

### 10.9 Server/API

State:

- Static file serving and route validation exist.
- Diff route rate-limited.
- Admin auth fail-open if key absent.
- CORS too broad.
- WebSocket lifecycle weak.
- Lab live test endpoint too permissive.
- Blocking reads inside async endpoints.

Next action:

- Harden production defaults.
- Add API contract and abuse tests.

### 10.10 Frontend

State:

- Multiple pages and modules exist.
- Lab is feature-rich but split-brain.
- Remote dependencies remain.
- Placeholder key material remains.
- Production deploy bypasses Vite output.
- Static/no-JS degraded state is weak.

Next action:

- Make frontend local-first, build-driven, no-placeholder, and no-network smoke-tested.

### 10.11 Docs

State:

- Extensive docs exist.
- Many docs are stale, duplicated, or contradictory.
- Generated debt artifacts are noisy.

Next action:

- Make docs generated/validated from canonical manifests where possible.

### 10.12 Tests

State:

- Large test suite passes locally after dev deps.
- Browser tests can skip.
- Mypy does not check many untyped function bodies.
- Workflow invalidity prevents trusting CI enforcement.

Next action:

- Repair CI.
- Split required test profiles.
- Add public artifact and deployed frontend smoke tests.

### 10.13 Go and Rust

State:

- Go sidecar supports chain arrays and panic recovery.
- WASM tester is constrained to browser JS/WebSocket.
- Rust SS FFI is optional and deterministic: it runs only with a local binary
  plus configured `SS_LIB_SHA256`, otherwise the Python validation path remains
  authoritative; configured hash mismatches fail closed.

Next action:

- Document WASM runtime boundaries and continue hardening optional native
  components.

---

## 11. Project-Document Claim Completion Program

This audit is not only a bug-fix plan. It is also a plan to finish every capability the project documents claim. The rule is simple: **a claim is not allowed to remain in README, STATUS, wiki, SECURITY, docs, AGENTS, frontend copy, or changelog unless it is implemented, tested, deployed, and observable.**

### 11.1 Claim Ledger

Created `docs/claim_ledger.json` as the first canonical claim ledger and
`scripts/validate_claim_ledger.py` as the guardrail. It is intentionally a
living ledger: it captures closed claims with proof and keeps broader claims as
`partial` or `planned` until code, tests, docs, frontend surfaces, output
artifacts, and cleanup decisions are all aligned.

Each claim entry must include:

- claim text
- source file and line
- product area
- status: `complete`, `partial`, `planned`, `experimental`, `deprecated`, or `removed`
- canonical owner file/module
- tests proving it
- frontend surface proving it, if user-facing
- output artifact proving it, if artifact-facing
- docs updated
- changelog entry
- cleanup/removal decision

No claim may be closed as complete without proof across code, tests, docs, and public/deployed behavior.

Validation: `python scripts/validate_claim_ledger.py` and `python -m pytest
tests/unit/test_validate_claim_ledger.py -q` passed locally.

### 11.2 Claimed Capability Areas That Must Be Completed Or Removed

The project documents currently claim or strongly imply the following capability groups. Each group must be finished completely or explicitly demoted.

#### A. Streaming Pipeline Architecture

Claimed capability:

- producer/consumer streaming pipeline
- bounded queues
- adaptive timeouts
- circuit breakers
- fail-open/fail-safe source handling
- time-limited batch execution
- partial output generation
- source quality tracking
- dynamic resharding

Completion requirements:

1. Workflows must run the actual pipeline reliably.
2. Queue pressure must not corrupt source-quality scoring.
3. Time-limited runs must publish valid degraded outputs.
4. Source quality and resharding must use run IDs and avoid races.
5. Docs must explain exact failure modes and degraded behavior.

Tests/proof:

- overloaded queue test
- source failure vs runner backpressure test
- time-limited output test
- reshard no-loop workflow test
- generated `health.json` proof

#### B. Protocol Support

Claimed capability:

- VLESS
- VMess
- Trojan
- Shadowsocks
- SSR
- Hysteria
- Hysteria2
- TUIC
- WireGuard
- SSH
- SOCKS/SOCKS4/SOCKS5
- HTTP/HTTPS normalization
- OpenVPN
- other supported protocols in `proxy.schema.json`

Completion requirements:

1. Done for inventory: `docs/protocol_matrix.json` is the canonical protocol
   matrix and `scripts/validate_protocol_matrix.py` checks it against
   `schema/proxy.schema.json`, parser exports, README protocol claims, and
   frontend display capability.
2. For every protocol, list parser support, validation support, tester support, Sing-box export support, Clash export support, Base64/plaintext support, frontend display support, and known limitations.
3. Delete protocol claims with no parser/export/test path.
4. Add malformed-input tests for every parser.
5. Add golden output tests for every supported protocol.

Current status: remediated for the protocol-matrix inventory claim. The matrix now separates canonical protocols, input
aliases, schema-only compatibility markers, and internal markers.
`tests/unit/test_protocol_output_golden.py` checks every public canonical
protocol fixture against the matrix's Sing-box/Clash export flags and generated
subscription output, then parses every public protocol sample and sends the
resulting proxy records through the real frontend `processProxyData()`
normalizer. The same golden file now also checks representative malformed input
for every public canonical parser and requires fail-closed `None` results.
`scripts/frontend_same_origin_smoke.cjs` also serves fixture `proxies.json` data
for every public canonical protocol and verifies browser-rendered Proxies page
protocol badges plus protocol filter options in Chromium. Deeper
protocol-specific fuzzing remains a separate parser-hardening track.
This checkpoint also tightens missing-credential handling for TUIC, Snell,
Brook, and SSH authorities. Hysteria/Hysteria2 anonymous mode and generic
HTTP/SOCKS unauthenticated proxies remain preserved as compatibility behavior.
The VLESS/VMess boundary is now documented by tests rather than tightened in a
regression-prone parser path: VLESS query-parameter UUID recovery remains
covered, VMess missing/empty IDs are malformed parser fixtures, public protocol
goldens use UUIDv4 values compatible with the schema, and missing VMess/VLESS
UUIDs remain fatal in the security validator even when insecure proxy retention
is enabled.
Shadowsocks credential fallback also preserves the intended compatibility path:
host-side password/pass/psk/pwd query parameters are parsed before the
empty-password drop, so fallback credentials are recovered while links with no
credential material still fail closed.
Clash JSON imports now use the same fail-closed parser posture for malformed
entries: missing VMess/VLESS UUIDs, missing Trojan/Shadowsocks credentials,
invalid Shadowsocks methods, invalid ports, empty WireGuard private keys, and
unknown imported types are rejected before they can become public proxy records.

Tests/proof:

- per-protocol parse fixtures
- per-protocol conversion fixtures
- per-protocol output artifacts
- frontend render fixture for protocol badges/details

#### C. Output Families

Claimed capability:

- `base64.txt`
- `chosen/base64.txt`
- `base64-dns-safe.txt`
- DNS-hardened variants
- `singbox.json`
- `singbox-vpn.json`
- `singbox-chains.json`
- Clash YAML
- protocol-specific files
- side-product ZIPs
- `proxies.json`
- `metadata.json`
- revived/washed/smart-chain/shielded outputs

Completion requirements:

1. Every output must be in `artifact_manifest.json`.
2. Every output must have schema/format validation.
3. Empty/degraded versions must be valid.
4. Chosen outputs must be provably selected from a documented ranking rule.
5. DNS-safe and DNS-hardened semantics must be tested and documented.
6. Side-product ZIP contents must be manifest-listed and secret-scanned.

Tests/proof:

- golden output test
- zero-working output test
- DNS-safe/hardened differential test
- ZIP content manifest test
- deployed artifact smoke test

Checkpoint update:

- `docs/output_matrix.json` now inventories the current Pages-required public outputs by family, category, format, nonempty requirement, schema-validation flag, and degraded-output validity.
- `scripts/validate_output_matrix.py` checks the matrix against `scripts/validate_pages_artifact.py` and the side-product generator contract so required artifact coverage, nonempty semantics, required ZIP members, and optional OpenVPN/WireGuard member patterns cannot drift silently.
- `tests/unit/test_validate_output_matrix.py` covers current-repo acceptance, generated output docs parity, missing required output detection, and nonempty-flag drift.
- `scripts/run_test_profile.py` now includes the output-matrix validator and focused tests in `production-smoke`.
- `scripts/validate_pages_artifact.py` now checks side-product ZIP integrity, rejects unsafe member paths, and requires the stable `proxies.txt` member in universal, DNS-safe, and DNS-hardened ZIP bundles.
- Side-product ZIP validation now rejects deploy/CI secret assignments and placeholder markers in ZIP members while allowing normal proxy credentials and WireGuard/OpenVPN material.
- Sing-box artifact validation now checks unique outbound tags, selector/urltest references, outbound detours, route rule outbounds, and DNS detours. Clash artifact validation now checks proxy/group names, group references, and rule policy references.
- `scripts/generate_output_docs.py` now renders the README and API-reference output tables from `docs/output_matrix.json`; `production-smoke` runs it in `--check` mode so hand-maintained output table drift fails.
- `scripts/validate_pages_artifact.py --native-client-check` now runs `sing-box check -c` for Sing-box outputs and `mihomo -t -f` / Clash-compatible config tests for Clash outputs when local binaries are available. Missing native binaries are treated as a clean skip so the zero-budget path remains intact.
- `tests/unit/test_output.py` now builds a deterministic Pages-style artifact from the real output generator, adds deploy aliases and static placeholder files, refreshes `health.json` / `artifact_manifest.json`, and validates the complete directory with `scripts/validate_pages_artifact.py`.
- `tests/unit/test_protocol_output_golden.py` now provides per-protocol generator/export golden fixtures for every public canonical protocol, checks the protocol matrix's Sing-box/Clash export flags against actual converters, checks generated Sing-box/Clash configs, and decodes the Base64 subscription output to assert representative URI families survive generation.
- `tests/unit/test_protocol_output_golden.py` now also parses sample strings for every public canonical protocol and imports `frontend/assets/js/proxies.js` from Node to verify the real `processProxyData()` normalizer preserves the expected protocol labels.
- `tests/unit/test_protocol_output_golden.py` now includes representative malformed inputs for every public canonical parser and asserts they fail closed without being accepted.
- `scripts/frontend_same_origin_smoke.cjs` now serves browser fixture `proxies.json` / `metadata.json` data for every public canonical protocol and checks rendered Proxies page protocol badges plus filter options while still blocking non-same-origin runtime requests.
- `src/configstream/parsers/others.py` now drops TUIC, Snell, Brook, and SSH links that omit mandatory credential material, with focused parser regressions covering those edges.

Remaining:

- None for the current public output-family contract. Continue the separate parser-hardening track for malformed-input depth and the broader deployment-readiness roadmap.

#### D. WARP, Vwarp, Washing, Revival, Shielding, and Smart Chains

Claimed capability:

- WARP revival
- Vwarp revival
- MASQUE/AtomicNoize/Psiphon options
- WARP shielding
- smart chains
- WARP-in-WARP / double WARP
- preserved failed revived candidates

Completion requirements:

1. Separate candidate generation from verified success.
2. Retest anything counted as working.
3. Label failed-but-kept candidates honestly.
4. Make Vwarp strategy support consistent across backend, frontend Lab, docs, and exports.
5. Confirm all WARP WireGuard outbounds include `mtu: 1280`.
6. Add safe fallback when Vwarp binary is absent.

Tests/proof:

- washer unit tests for each strategy
- metric invariant tests
- Lab strategy tests
- generated chain schema tests
- frontend labels for candidate vs verified chain

#### E. Chain Laboratory

Claimed capability:

- five-step guided chain builder
- proxy URI parsing
- clean Cloudflare IP discovery
- local/manual scan modes
- WARP, Double WARP, Vwarp MASQUE, Vwarp AtomicNoize, WARP+Psiphon, Relay Chain, TLS Fragment, CDN Worker, Custom JSON
- advanced evasion options
- live or manual testing
- exports: Sing-box JSON, Clash YAML, Xray JSON, Nekobox link, URI, QR, Python script, Bash script
- offline lab support

Completion requirements:

1. Create canonical lab strategy registry.
2. Every UI option must have a JS builder.
3. Every builder must have export support.
4. Every export must be tested.
5. Live testing must be safe and production-disabled unless explicitly enabled.
6. QR generation must be local/offline.
7. Offline lab must match online lab capabilities or clearly document differences.

Tests/proof:

- one browser test per strategy
- one export test per export format
- no-network QR test
- no-JS/manual fallback test
- lab XSS test

#### F. Frontend Public Site

Claimed capability:

- homepage dashboard
- proxies table
- analytics dashboard
- wiki pages
- about page
- lab/offline lab
- health/trust state
- client-side verification
- static hosting compatibility
- IPFS/failover behavior

Completion requirements:

1. Production deploy path must match tested build path.
2. Static/no-JS fallback must be useful.
3. Public pages must never show unresolved placeholders.
4. Public pages must show freshness and degraded reasons.
5. Verification must either work or be removed as a claim.
6. Remote runtime dependencies must be optional, not required.
7. IPFS/failover claims must be proven or demoted.

Tests/proof:

- browser tests
- no-JS snapshot tests
- placeholder leak tests
- deployed smoke tests
- local-only asset test

#### G. Security Claims

Claimed capability:

- sanitized logging
- input validation
- blocklist enforcement
- no active scanning by default
- admin auth
- secure frontend verification
- anti-abuse posture
- safe defaults

Completion requirements:

1. Production admin endpoints fail closed.
2. Logs are sanitization-tested.
3. Fetcher blocks SSRF/private targets by default.
4. Lab live testing is safe and bounded.
5. CORS is explicit.
6. Private IP allowance is documented as local/dev-only or made false by default.
7. SECURITY.md must match runtime behavior exactly.

Tests/proof:

- security unit tests
- route auth tests
- CORS tests
- SSRF redirect tests
- log sanitization tests

#### H. CI/CD, Zero Budget, and Publication

Claimed capability:

- GitHub Actions pipeline
- GitHub Pages deployment
- 17 batch shards
- four-hour target batch timing
- retest workflow
- release workflow
- optional mirrors
- no paid required infrastructure

Completion requirements:

1. All workflows parse and run.
2. Core pipeline works without optional paid/account services.
3. Optional mirrors are clearly optional and never required for success.
4. Artifact publication is deterministic and traceable.
5. Batch count and timing docs match code.
6. Retest and release workflows are real gates.

Tests/proof:

- workflow lint
- workflow dry-run/check
- artifact manifest
- deploy smoke test
- no-secret core CI test

#### I. Documentation and Governance

Claimed capability:

- production-ready status
- finalization reports
- release hardening
- zero TODO/FIXME
- debt matrix
- roadmap process
- complete wiki

Completion requirements:

1. Remove production-ready claims until final gate passes.
2. Regenerate debt matrix portably.
3. Merge duplicate docs trees.
4. Ensure docs reference no removed files.
5. Validate docs against canonical manifests.

Tests/proof:

- docs drift tests
- claim ledger
- link/path tests
- changelog validation

### 11.3 Claim Closure Workflow

For each claim group:

1. Inventory all claims from docs/frontend/status/changelog.
2. Pick one canonical owner.
3. Implement missing behavior or remove/demote the claim.
4. Add tests.
5. Update frontend/backend/docs/schema parity.
6. Delete deprecated code/docs.
7. Update changelog.
8. Run validation.
9. Mark claim complete only after deployed/public proof exists.

### 11.4 High-ROI Refinements To Add While Closing Claims

These are not just nice-to-haves. They reduce future drift and make the project easier to keep production-ready.

1. **Generate docs from manifests:** Use `artifact_manifest.json`, `protocol_matrix.json`, and `lab_strategies.json` to generate README tables and wiki matrices.
2. **Single production health file:** Add `health.json` with status, freshness, degraded reasons, run ID, source commit, artifact counts, and validation results.
3. **Public contract tests:** Add a test that runs output generation and validates every public artifact against schema/manifest.
4. **No-placeholder gate:** Add a CI check for unresolved `{tokens}`, placeholder keys, example secrets, and stale production-ready claims.
5. **No-network frontend mode:** Add a browser test where all non-same-origin requests are blocked and core pages still work.
6. **Security posture test suite:** Add focused tests for CORS, admin auth, SSRF, log sanitization, lab endpoint policy, and private IP handling.
7. **Docs drift bot/script:** Add a local script that reports docs claims not backed by a canonical manifest.
8. **Run provenance everywhere:** Add `trace_id`, `source_commit`, `workflow_run_id`, and artifact hashes to metadata and frontend health display.
9. **Strict dependency hygiene:** Gate `npm audit`, remove yanked Python pins, and separate core deps from optional mirror/lab extras.
10. **Degraded-output UX:** Build first-class UI for stale, partial, time-limited, zero-working, and validation-failed states instead of generic loading/failure text.
11. **Golden fixtures:** Maintain small deterministic fixtures for each protocol and each output family.
12. **One cleanup script:** Add a maintenance script that checks generated artifacts, ignored outputs, duplicate docs, empty assets, and removed-path references.

---

## 12. Finalized Remediation Roadmap

### Phase 0 - Freeze and Baseline

Goal: stop changing product features until the project has a reliable baseline.

Tasks:

1. Freeze feature work.
2. Create a remediation branch.
3. Record current public artifact state.
4. Record current local validation results.
5. Mark `STATUS.md` as "remediation in progress, not production-ready".
6. Add this audit report as the active source of truth.

Parity check:

- README, STATUS, SECURITY, wiki, and frontend banners must agree that remediation is active.

Cleanup:

- Delete old audit appendices only by replacing them with this single report.

Changelog:

- Add an entry for audit reset and production-readiness reclassification.

### Phase 1 - Restore CI/CD Truth

Goal: make automation parse, run, and enforce what docs claim.

Tasks:

1. Fix YAML indentation in all workflows.
2. Add `actionlint`.
3. Add workflow YAML parser script.
4. Add pre-commit workflow lint hook.
5. Repair `validate_versions.py` encoding issues.
6. Re-run CI-equivalent local gates.
7. Update workflow docs.

Parity check:

- `.github`, README, docs/wiki/project/05-devops.md, STATUS, and CHANGELOG all describe the same workflow set.

Cleanup:

- Remove any dead workflow env var blocks or unused secrets.

Changelog:

- List every workflow repaired and every validation command added.

### Phase 2 - Stop Workflow Loops and Artifact Races

Goal: remove self-triggering and mixed-artifact deployment.

Tasks:

1. Isolate resharding from full pipeline runs.
2. Add `paths-ignore` or an equivalent safe trigger design.
3. Add workflow concurrency groups for pipeline, retest, deploy, and mirror.
4. Ensure deploy consumes exactly one artifact bundle from exactly one completed run.
5. Add run ID, trace ID, and source commit SHA to metadata and manifest.

Parity check:

- Workflow files, metadata schema, frontend health display, and docs all expose the same run identity fields.

Cleanup:

- Delete old bot-commit behavior if no longer canonical.

Changelog:

- Document the new run ownership and concurrency model.

### Phase 3 - Canonicalize Public Artifact Contracts

Goal: one truth for every output.

Tasks:

1. Define `artifact_manifest.json`.
2. Define or update `metadata.schema.json`.
3. Define or update `proxy.schema.json`.
4. Decide canonical `proxies.json` shape.
5. Remove rejected shape from code and docs.
6. Add schema validation in CI and deploy.
7. Add public artifact smoke tests.

Parity check:

- Output generator, server routes, frontend fetchers, README, API docs, schemas, and tests all match.

Cleanup:

- Delete legacy schema branches and old docs examples.

Changelog:

- Mark any public schema breaking change clearly.

### Phase 4 - Fix Metrics and Trust Signals

Goal: make public numbers honest.

Tasks:

1. Fix shielded candidate accounting.
2. Separate native, revived, shielded candidate, shielded verified, smart chain, and total counts.
3. Make `success_rate` formula explicit.
4. Add metric invariant tests.
5. Update frontend analytics labels.
6. Update docs.

Parity check:

- Backend stats, metadata schema, frontend charts, docs, and tests agree on every metric.

Cleanup:

- Delete old aliases that keep inflated semantics alive.

Changelog:

- Include before/after metric definitions.

### Phase 5 - Harden Server Security Defaults

Goal: production fails closed where it should.

Tasks:

1. Require admin auth in production.
2. Tighten CORS.
3. Add WebSocket heartbeat/idle/connection limits.
4. Disable lab live test in production by default.
5. Add payload-size and schema validation for lab live test.
6. Replace blocking async route reads.
7. Add SSRF-safe fetch/redirect validation.

Parity check:

- Runtime settings, `.env.example`, SECURITY.md, API docs, tests, and frontend behavior agree.

Cleanup:

- Delete permissive production fallbacks.

Changelog:

- Mark production security breaking changes.

### Phase 6 - Make Frontend Production-Real

Goal: deployed frontend equals tested frontend.

Tasks:

1. Choose Vite build or raw static, not both.
2. If Vite is canonical, deploy `frontend-dist`.
3. If raw static is canonical, remove Vite build claims.
4. Inject public config through a generated file.
5. Fail build on placeholder keys.
6. Make frontend local-first and self-host critical assets.
7. Remove external QR service.
8. Fix Lab XSS surfaces.
9. Add no-JS/degraded-state tests.
10. Add browser tests for every lab strategy.

Parity check:

- Deployed HTML/JS, build config, workflow, docs, and tests use the same frontend production path.

Cleanup:

- Delete unused build path, unused scripts, and placeholder config files.

Changelog:

- Include production frontend path and deleted legacy path.

### Phase 7 - Clean Docs and Governance

Goal: docs become accurate and maintainable.

Tasks:

1. Rewrite `STATUS.md` from real gates.
2. Update README output tables.
3. Update SECURITY.md to match runtime defaults.
4. Merge or generate duplicate encyclopedia docs.
5. Regenerate debt matrix with repo-relative paths.
6. Exclude generated artifacts from self-scans.
7. Normalize lab strategy count everywhere.
8. Remove stale module references.

Parity check:

- Docs must be checked by automated tests against canonical manifests.

Cleanup:

- Delete duplicate docs tree if generation replaces it.

Changelog:

- Include docs deleted, generated, or canonicalized.

### Phase 8 - Dependency and Supply-Chain Cleanup

Goal: dependency state matches production claims.

Tasks:

1. Update Vite/picomatch/postcss to patched versions.
2. Replace yanked `numpy==2.4.0`.
3. Add `npm audit` gate with documented exceptions only.
4. Add Python dependency audit or lock review.
5. Pin GitHub Actions by version and consider SHA pinning for critical actions.
6. Review optional external service scripts.

Parity check:

- package files, requirements, docs, CI, and changelog all state the same dependency policy.

Cleanup:

- Remove unused deps and stale lock entries.

Changelog:

- Include security advisories fixed and dependency changes.

### Phase 9 - Complete Documented Claims And High-ROI Refinements

Goal: make every project-document claim true, observable, and maintainable.

Tasks:

1. Create the claim ledger.
2. Inventory README, STATUS, SECURITY, wiki, roadmap, changelog, AGENTS, and frontend claim text.
3. Complete or remove each claim.
4. Add canonical manifests for protocols, artifacts, lab strategies, and production health.
5. Generate docs tables from those manifests.
6. Add no-placeholder, no-network frontend, public contract, and security posture tests.
7. Delete every stale compatibility branch after each claim is migrated.
8. Update changelog after each claim group is closed.

Parity check:

- Claim ledger, code, tests, docs, frontend, schemas, workflows, and deployed artifacts agree.

Cleanup:

- Remove every demoted/deprecated claim from public docs and UI.

Changelog:

- Include one entry per claim group completed or removed.

### Phase 10 - Final Production Readiness Gate

Goal: only mark ready when all public surfaces prove it.

Required final commands:

```text
python -m compileall -q src scripts tests
python scripts/validate_versions.py
python -m flake8 src tests
python -m black --check .
python -m mypy .
pytest
npm ci
npm audit
npm run build
workflow YAML parse check
actionlint
artifact schema validation
frontend browser tests
deployed public smoke test
```

Required final public checks:

- `metadata.json` validates.
- `artifact_manifest.json` validates.
- `health.json` exists and is current.
- universal, chosen, DNS-safe, DNS-hardened, Clash, Sing-box, chain, and side-product outputs are present or explicitly degraded.
- frontend has no unresolved placeholders.
- no placeholder key material is deployed.
- public docs do not claim stale test counts.

Final status rule:

- Only after this phase may `STATUS.md`, README, pyproject classifier, and public homepage say production-ready.

---

## 13. Detailed Implementation Checklists

### 13.1 Workflow Checklist

- Parse every YAML file.
- Run `actionlint`.
- Verify all `env:` indentation.
- Verify triggers.
- Verify permissions are least-privilege.
- Verify no workflow can self-trigger a full expensive run accidentally.
- Verify `concurrency` prevents overlapping deploys.
- Verify deploy consumes one artifact generation.
- Verify CI gates are required.
- Verify Pages deploy has post-deploy smoke tests.

### 13.2 Backend Checklist

- No blocking disk reads in async endpoints for large files.
- Admin endpoints fail closed in production.
- CORS is explicit and minimal.
- Lab live test is disabled or protected in production.
- Fetcher validates final resolved targets after redirects.
- Logs sanitize endpoints, credentials, UUIDs, tokens, and configs.
- Metrics do not count untested candidates as working.
- Shutdown closes DB connections, subprocesses, and background tasks.
- Concurrency ownership is documented and tested.

### 13.3 Frontend Checklist

- Production deploy uses the same frontend build that CI tests.
- No placeholder keys.
- No unresolved template tokens.
- No remote dependency required for core UI.
- No user data sent to external QR or analytics services.
- Untrusted content never goes into `innerHTML`.
- Lab strategy options are generated from canonical data.
- No-JS fallback shows useful links, freshness, and degraded state.
- Browser tests cover homepage, proxies page, analytics, wiki, lab, and offline lab.

### 13.4 Output Contract Checklist

- `metadata.json` schema-valid.
- `proxies.json` schema-valid.
- `artifact_manifest.json` exists.
- `health.json` exists.
- All output counts are internally consistent.
- Chosen output selection is documented.
- DNS-safe and DNS-hardened behavior is documented and tested.
- Empty/degraded outputs are valid and labeled.
- Side-product ZIP content is manifest-listed and secret-scanned.

### 13.5 Docs Checklist

- README matches implementation.
- SECURITY.md matches runtime defaults.
- STATUS.md is evidence-based.
- CHANGELOG.md updated after every step.
- Wiki API docs match schemas.
- Lab strategy count matches UI.
- Removed files are not referenced.
- Generated docs use repo-relative paths.
- Duplicate docs are generated from one source or deleted.
- Referenced static frontend assets exist and are non-empty.

### 13.6 Cleanup Checklist

- Delete legacy files after migration.
- Delete old aliases.
- Delete duplicate helpers.
- Delete stale docs.
- Delete unused config flags.
- Delete unused frontend code paths.
- Delete old schema branches.
- Delete ignored build output before commit unless intentionally tracked.
- Verify `git status --short` is clean except intended changes.

---

## 14. Final Production-Ready Definition

ConfigStream is production-ready only when:

1. All workflows parse and required checks run.
2. CI cannot silently skip core validation.
3. Scheduled workflows cannot self-trigger loops.
4. Deploy cannot publish mixed artifacts.
5. Public artifacts are current, schema-valid, and manifest-described.
6. Degraded output is explicit, valid, and useful.
7. Metadata counts are honest.
8. Security defaults fail closed in production.
9. Frontend deploy path is the tested build path.
10. Frontend has no placeholder keys or unresolved template tokens.
11. No sensitive user payload is sent to third-party QR/runtime services.
12. Docs, schemas, frontend, backend, tests, and workflows all share one truth.
13. No deprecated compatibility layer remains after cleanup.
14. Changelog records every remediation step.

Until then, the correct public status is:

```text
Remediation in progress. Not production-ready. Public artifacts may be stale or degraded.
```
