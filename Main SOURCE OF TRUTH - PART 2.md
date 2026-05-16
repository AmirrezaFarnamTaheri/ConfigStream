
### 0. Global implementation rule for every future feature

Before adding any capability, define the contract first.

Every feature should answer:

**What does it do?**
What user or pipeline problem does it solve?

**Where does it live?**
Backend, pipeline, parser, tester, output generator, online lab, offline lab, frontend, CI, docs, or schema.

**What is the safety boundary?**
Can it make network requests? Can it run processes? Can it expose secrets? Can it scan? Can it mutate outputs?

**What is the degraded behavior?**
What happens when no proxies work, no DNS resolves, a binary is missing, a source is down, GitHub rate-limits, browser APIs fail, or the user is offline?

**How is it proven?**
Unit tests, integration tests, generated output fixtures, browser tests, visual screenshots, public artifact validation, native client validation, and live deploy smoke.

**How is it documented?**
README, wiki, STATUS, SECURITY, CHANGELOG, output matrix, protocol matrix, claim ledger, lab docs, operator docs.

**How is it removed or rolled back?**
Every experimental feature should have a kill switch and a cleanup path.

Universal checklist for every item:

- Add a feature flag if behavior is experimental or high-risk.
- Add schema fields only after deciding versioning and defaults.
- Add tests before marking the item complete.
- Add no-placeholder/no-secret/no-raw-log checks when touching frontend, outputs, logs, or ZIPs.
- Add degraded-state tests.
- Update `CHANGELOG.md`.
- Update `STATUS.md`.
- Update `docs/claim_ledger.json` only when the claim has proof.
- Update `docs/output_matrix.json` if a public artifact changes.
- Update `docs/protocol_matrix.json` if protocol behavior changes.
- Add generated screenshots for frontend/lab changes.
- Add public artifact validation when outputs change.

### 1. Backend architecture and core maintainability

#### 1.1 Create a capability registry

##### Purpose

ConfigStream has many capabilities: parsing, testing, WARP, Vwarp, DNS-safe outputs, DNS-hardened outputs, smart chains, online lab, offline lab, frontend verifier, output formats, optional mirrors, browser checks, WASM checks, and more.

A **capability registry** would make all of these explicit in one machine-readable place.

##### What to build

Create a canonical file such as:

`docs/capability_registry.json`

Each capability should include:

- ID: `pipeline.fetch.adaptive_timeout`
- Name: `Adaptive source fetching`
- Area: `pipeline`, `lab`, `frontend`, `outputs`, `security`
- Status: `stable`, `experimental`, `partial`, `planned`, `deprecated`
- Owner files
- Feature flag
- Required dependencies
- Required secrets
- Public artifacts affected
- Tests
- Docs
- Safety notes
- Degraded behavior
- Rollback instructions

##### Why it matters

This prevents the project from claiming capabilities that are only partially implemented. It also gives the online/offline lab a way to render “available,” “experimental,” and “not available in this environment” states automatically.

##### Implementation instructions

1. Create `docs/capability_registry.json`.
2. Create `scripts/validate_capability_registry.py`.
3. Require every `stable` capability to include tests, docs, owner files, and changelog proof.
4. Add a frontend helper that can optionally read a published copy.
5. Add CI validation.
6. Add documentation explaining statuses.

##### Checklist

- Registry exists.
- Registry has schema validation.
- CI fails if a stable capability lacks proof.
- Frontend/lab can display capability state.
- README no longer hardcodes capability claims that should come from the registry.
- Changelog documents the new governance mechanism.

#### 1.2 Create a module ownership map

The project has many modules and historical refactors. A module ownership map prevents duplicate helpers, stale aliases, and unclear responsibilities.

Create:

`docs/module_ownership.json`

Each module entry should include:

- Path
- Owner domain
- Public APIs
- Internal-only APIs
- Disallowed duplicate or removed-module imports
- Replacement for removed modules
- Tests that cover it
- Docs that describe it

Example:

```json
{
  "src/configstream/output_logic.py": {
    "domain": "output-generation",
    "public_functions": ["generate_categorized_outputs", "write_public_artifact_contract"],
    "disallowed_duplicates": ["artifact manifest writer in deploy shell"],
    "tests": ["tests/unit/test_output.py"],
    "docs": ["docs/output_matrix.json"]
  }
}
```

This helps prevent reintroducing removed modules or creating parallel implementations.

1. Create the map.
2. Add validator that checks removed module names are not imported.
3. Add import-boundary tests.
4. Use it in contributor docs.
5. Generate a module map page in docs.

- Every major `src/configstream` area is mapped.
- Removed modules are explicitly listed.
- Validator fails on imports that reintroduce removed modules or duplicate canonical helpers.
- Docs explain canonical module paths.
- AGENTS/module docs match the map.

#### 1.3 Add a stable internal event bus

Pipeline modules currently pass stats, queues, logs, files, and side effects through direct calls. A structured internal event bus would make observability and plugins cleaner.

A lightweight typed event system:

- `SourceFetchStarted`
- `SourceFetchSucceeded`
- `SourceFetchFailed`
- `ProxyParsed`
- `ProxyDropped`
- `ProxyValidated`
- `ProxyTested`
- `ProxyRevived`
- `OutputWritten`
- `ArtifactValidated`
- `PipelineDegraded`
- `PipelineCompleted`

This improves tracing, analytics, plugin support, and debugging. It also avoids scattering metric increments across many modules.

1. Add `src/configstream/events.py`.
2. Define event dataclasses or Pydantic models.
3. Add an in-memory event collector for one run.
4. Add optional JSONL event output.
5. Replace ad hoc metric updates gradually.
6. Keep hot-path overhead low.
7. Add event sampling for high-volume parser drops.

- Events are typed.
- Events include `trace_id`.
- Sensitive values are sanitized before event emission.
- Pipeline can run with event collection disabled.
- Output includes optional `pipeline_events.jsonl` only when enabled.
- Tests verify event order for a minimal pipeline.

#### 1.4 Add a plugin architecture

ConfigStream can grow faster if parsers, output adapters, test engines, lab strategies, and source providers follow plugin contracts.

##### Plugin areas

- Source providers
- Parsers
- Validators
- Testers
- Scorers
- Washers
- Chain builders
- Output adapters
- Lab strategies
- Frontend panels
- Mirror publishers

1. Define plugin interfaces.
2. Keep built-in plugins first.
3. Add plugin discovery through explicit registry, not arbitrary dynamic imports.
4. Require plugin metadata.
5. Add security rules: no network access unless declared.
6. Add test fixture for a dummy plugin.
7. Add docs for creating a plugin.

- Plugin registry exists.
- Built-in parser/output/lab strategy registration works.
- Unknown plugins fail closed.
- Plugin capability metadata appears in capability registry.
- Plugin tests cover enable/disable behavior.
- Unsafe plugin behavior is blocked by policy.

### 2. Source ingestion and acquisition

#### 2.1 Source provider abstraction

Right now source files are URL lists. A richer source model would allow local files, remote URLs, GitHub raw files, user-provided bundles, mirrors, and curated source groups.

##### What to add

A source object shape:

```json
{
  "id": "source.github.v2ray.example",
  "url": "...",
  "type": "subscription",
  "protocol_hint": "mixed",
  "trust_level": "public",
  "region_hint": "global",
  "enabled": true,
  "rate_limit_group": "github-raw",
  "expected_format": "text-or-base64",
  "owner": "community",
  "notes": "High churn"
}
```

Raw URL lists are difficult to score, throttle, deduplicate, and explain. Structured source metadata enables better fetching and reporting.

1. Add `sources/sources.json`.
2. Keep existing `batch_*.txt` as generated shards.
3. Generate shards from `sources.json`.
4. Track source ID through the pipeline.
5. Include source ID in parse/test/drop metrics.
6. Add validator for source schema.
7. Add migration script from text batches to source objects.

- Structured source inventory exists.
- Existing batch files are generated or cross-checked.
- Source IDs appear in metadata.
- Source quality DB uses source IDs.
- Docs explain how to add a source.
- Invalid source objects fail validation.

#### 2.2 Source quality scoring v2

A source should not be judged only by whether it fetched. It should be scored by usefulness, stability, freshness, duplication rate, parse yield, working yield, security drops, latency, and churn.

##### Metrics to track

- Fetch success rate
- Average fetch duration
- Timeout count
- HTTP error count
- Content size
- Parseable line count
- Valid proxy count
- Working proxy count
- Duplicate rate
- Malformed rate
- Blocked/private endpoint rate
- Unique protocol diversity
- Last successful fetch
- Last meaningful output
- Churn rate
- Historical trust score

1. Extend source quality DB schema.
2. Add migration path.
3. Add per-source run record.
4. Use rolling windows: 1 run, 24h, 7d, 30d.
5. Add source state: `healthy`, `probation`, `dead`, `cooldown`, `manual-review`.
6. Add a source quality report artifact.
7. Feed source quality into dynamic resharding.

- DB migration tested.
- Source trust score is explainable.
- Bad sources are cooled down, not permanently deleted automatically.
- Source report is generated.
- UI can show source health summary.
- Changelog explains scoring changes.

#### 2.3 Adaptive source scheduler

Instead of fetching all sources equally every run, schedule sources based on reliability, freshness, and diversity.

##### Scheduling modes

- Always fetch critical curated sources.
- Fetch high-yield sources every run.
- Fetch medium-yield sources every N runs.
- Cool down flaky sources.
- Probe dead sources occasionally.
- Prioritize sources not seen recently.
- Balance by protocol and region.

1. Build a scheduler that consumes source quality stats.
2. Add a dry-run report.
3. Add a deterministic seed for reproducibility.
4. Keep zero-budget constraints.
5. Ensure source diversity, not just highest score.
6. Add fairness rules so new sources get trial windows.
7. Log scheduler decisions.

- Scheduler decisions are deterministic with seed.
- New sources are not starved.
- Dead sources are probed at low frequency.
- Source diversity is preserved.
- Dynamic shards are balanced by estimated work, not only URL count.
- Scheduler report is published.

#### 2.4 Fetch sandbox and strict network policy

Source fetching is one of the riskiest parts of the system. It needs hard boundaries against SSRF, private networks, redirect abuse, huge payloads, decompression bombs, binary junk, and malicious content.

##### Enhancements

- DNS resolution safety before connection.
- Revalidate resolved IP after redirect.
- Block private, loopback, link-local, multicast, reserved ranges.
- Reject credentials in URLs.
- Cap redirects.
- Cap response size.
- Cap decompressed size.
- Detect suspicious binary payloads.
- Track MIME type mismatch.
- Track excessive HTML/JS payloads.
- Avoid leaking full source URLs in logs.

1. Add a resolver abstraction.
2. Add tests with fake DNS resolver.
3. Validate hostnames before and after DNS resolution.
4. Enforce response-size streaming limits.
5. Add decompression-size guard.
6. Add source fetch policy docs.
7. Add security tests for every blocked network class.

- Private literal blocked.
- Private DNS resolution blocked.
- Redirect to private IP blocked.
- HTTPS redirect blocked if unsafe.
- URL credentials rejected.
- Oversized content rejected safely.
- Logs mask query tokens.
- CI includes SSRF regression tests.

#### 2.5 Source content classifier

Sources may be raw URI lists, Base64 subscriptions, Clash YAML, Sing-box JSON, V2Ray JSON, HTML pages, Telegram exports, Markdown, or mixed blobs. A classifier can choose the best parser path.

A `ContentClassifier` that returns:

- `raw_uri_list`
- `base64_subscription`
- `clash_yaml`
- `singbox_json`
- `v2ray_json`
- `html`
- `markdown`
- `telegram_text`
- `unknown_binary`
- `mixed`

1. Implement classifier with cheap heuristics.
2. Do not parse huge content multiple times.
3. Return confidence score.
4. Let parser pipeline use classifier hints.
5. Track classifier accuracy in metrics.
6. Add golden fixtures.

- Classifier handles small/large payloads.
- Unknown binary is safely dropped.
- Base64 detection avoids false positives.
- YAML/JSON parser errors are contained.
- Content type appears in source report.
- Tests cover each class.

### 3. Parsing and protocol handling

#### 3.1 Parser contract v2

Every parser should return structured success or structured failure, not just `Proxy | None`.

##### Proposed parser result

```python
ParserResult(
    proxy=Proxy | None,
    status="parsed" | "dropped" | "unsupported" | "malformed",
    protocol="vless",
    reason="missing_uuid",
    warnings=["recovered_uuid_from_query"],
    source_span={ "line": 123 },
)
```

This gives precise drop analytics and prevents vague “0 parsed” output.

1. Add `ParserResult`.
2. Update parsers gradually.
3. Keep compatibility wrapper during transition.
4. Add structured drop reasons.
5. Add parser result aggregation.
6. Publish parser statistics.

- Every public parser returns or maps to `ParserResult`.
- Drop reasons are enumerated.
- Unknown reasons are not free-form strings.
- No raw config values appear in logs.
- Parser stats appear in metadata or side report.
- Tests cover success/warning/drop states.

#### 3.2 Strict mode and compatibility mode

Some users want maximum compatibility; others want fail-closed strictness. Separate the two modes explicitly.

##### Modes

**Strict mode**

- Drop missing credentials.
- Drop invalid UUIDs.
- Drop weak/unknown methods.
- Drop private endpoints.
- Drop unsupported fields.
- Prefer schema-clean output.

**Compatibility mode**

- Recover credentials from query params.
- Accept legacy ciphers if output clients support them.
- Keep untested candidates as `is_working=false`.
- Preserve parser warnings.

1. Add `PARSER_MODE=strict|compat`.
2. Define per-protocol behavior.
3. Add tests for both modes.
4. Reflect mode in metadata.
5. Add docs explaining tradeoffs.

- Strict and compatibility modes produce predictable differences.
- Defaults are documented.
- Security-sensitive deployments can force strict.
- Compatibility mode never marks unverified proxies as working.
- Output files include mode metadata.

#### 3.3 Protocol-specific fuzzing

Proxy URI parsing is fragile. Fuzzing catches malformed percent encoding, strange Unicode, missing ports, broken Base64, huge query strings, nested JSON, and parser crashes.

1. Add Hypothesis strategies for each protocol.
2. Generate valid and invalid examples.
3. Assert parsers never crash.
4. Assert invalid data drops safely.
5. Assert valid normalized fields survive.
6. Keep corpus fixtures for regressions.

- Fuzz tests exist for VLESS, VMess, Trojan, SS, SSR, Hysteria, Hysteria2, TUIC, WireGuard, SSH, HTTP, SOCKS, OpenVPN, Clash imports.
- No parser logs raw secrets during fuzz failures.
- Crash corpus is stored as sanitized fixtures.
- Fuzz tests have bounded runtime for CI.

#### 3.4 Import/export parity matrix

A protocol may be parseable but not exportable to every client. That distinction must be visible.

The existing protocol matrix already starts this separation. `protocol_matrix.json` Expand it into an import/export parity matrix.

##### Matrix dimensions

For each protocol:

- Parse URI
- Parse JSON/YAML import
- Validate security
- Test with Go sidecar
- Test with Python fallback
- Export Sing-box
- Export Clash/Mihomo
- Export URI
- Export Shadowrocket
- Export Surge
- Export Loon
- Export Quantumult X
- Export native side product
- Browser lab support
- Offline lab support

1. Extend `docs/protocol_matrix.json`.
2. Add generated docs table.
3. Add tests that matrix claims match actual converters.
4. Make frontend read/display unsupported export statuses.
5. Add warnings in lab exports.

- No output claims universal support incorrectly.
- Client-specific unsupported states are visible.
- Tests fail if matrix and code drift.
- README protocol list links to matrix.
- Lab prevents invalid export choices or warns clearly.

#### 3.5 Parser provenance and lineage

Every output proxy should be traceable back to a source ID, source run, parser, normalized protocol, validation result, and test result.

##### Fields to add internally

- `source_id`
- `source_url_hash`
- `source_batch`
- `source_fetch_timestamp`
- `parser_name`
- `parser_warnings`
- `normalization_version`
- `validation_status`
- `test_engine`
- `test_timestamp`
- `lineage_hash`

##### Public privacy rule

Do not expose raw source URLs if they contain tokens. Use source IDs and hashes.

- Internal lineage available.
- Public lineage sanitized.
- Artifact manifest can include lineage summary.
- Debug bundle can include full sanitized lineage.
- Tests verify no raw secrets leak.

### 4. Validation, security, and trust pipeline

#### 4.1 Multi-stage validation pipeline

Validation should be layered, not one large function.

##### Stages

1. Syntax validation.
2. Mandatory field validation.
3. Endpoint validation.
4. Credential format validation.
5. Protocol-specific validation.
6. Client-export compatibility validation.
7. Security policy validation.
8. Network test eligibility validation.

1. Create explicit validator stages.
2. Record stage failure reasons.
3. Let outputs include non-working candidates only if policy allows.
4. Add per-stage metrics.
5. Make frontend able to show “why dropped” aggregates.

- Each validation failure has stage and reason.
- Tests cover each stage.
- Validation does not mutate proxy unexpectedly.
- Security policy can be strict or compatibility.
- Logs are sanitized.

#### 4.2 Endpoint reputation layer

Avoid repeatedly testing obviously unsafe or bogus endpoints.

##### Signals

- Private/non-global IP
- Reserved domains
- Malformed hostnames
- Known honeypot patterns
- Repeated redirect/captive portal behavior
- TLS mismatch
- Unstable IP resolution
- Suspicious ports
- Known bad ASN list, if locally provided

1. Keep passive reputation only by default.
2. Do not perform active scanning.
3. Allow user-provided blocklists.
4. Keep reputation explainable.
5. Add expiration windows.
6. Add appeal/retry path for false positives.

- Reputation never logs raw credentials.
- Reputation can be disabled.
- False positives can be retried.
- Metrics show blocked-by-reputation count.
- Docs explain passive-only policy.

#### 4.3 Secret and credential safety

Proxy configs contain secrets by design. The project must never leak them accidentally.

##### Add checks for

- Logs
- Events
- Metadata
- Artifact manifests
- ZIP side products
- Frontend local storage
- Browser error messages
- Screenshots
- Test snapshots
- CI logs
- Debug bundles

1. Define a central secret masker.
2. Ban raw f-string logging in high-risk modules.
3. Add static tests.
4. Add runtime tests with known fake secrets.
5. Add screenshot redaction where needed.
6. Add debug bundle sanitizer.

- Fake UUID/password/token never appears in logs.
- CI logs are safe.
- ZIP members are scanned.
- Frontend does not display full secrets unless user explicitly opens raw config.
- Screenshots avoid secret dumps.

### 5. Tester engines and proxy quality

#### 5.1 Tester engine abstraction v2

ConfigStream uses Go sidecar and Python fallback, with browser/WASM checks being weaker. Make tester capability explicit.

##### Tester capabilities

- Raw TCP connect
- HTTP CONNECT
- SOCKS handshake
- TLS handshake
- QUIC support
- UDP support
- WireGuard support
- Chain testing
- DNS resolution path
- Exit IP check
- Captive portal detection
- Browser-only WebSocket reachability

1. Define `TesterCapabilities`.
2. Expose engine capabilities in metadata.
3. Add eligibility routing: choose engine based on protocol.
4. If engine cannot prove a protocol, mark result as `limited`.
5. Update frontend labels.

- Go sidecar capability reported.
- Python fallback capability reported.
- Browser checks labeled limited.
- Unsupported test combinations fail explicit, not silent.
- Metadata includes test engine summary.

#### 5.2 Multi-probe testing

One URL check is not enough. Some proxies pass one endpoint but fail another.

##### Probe types

- TCP connect
- TLS handshake
- HTTP 204 endpoint
- Cloudflare trace
- DNS resolution
- Exit IP
- Geo lookup
- Header integrity
- Latency sample
- Jitter sample

1. Add probe profile: `fast`, `balanced`, `deep`.
2. Keep default budget small.
3. Use deep tests only for candidates likely to be good.
4. Store probe result breakdown.
5. Score based on probe confidence.

- Fast mode is cheap.
- Deep mode is optional.
- Test budget is enforced.
- Metadata shows probe profile.
- No endpoint is hammered.
- Failures are categorized.

#### 5.3 Confidence scoring

Replace binary “working/not working” with confidence.

##### Proposed fields

- `is_working`
- `confidence_score`
- `test_confidence`
- `evidence_count`
- `last_tested_at`
- `test_engine`
- `failure_reason`
- `degraded_reason`

##### Score inputs

- Test success
- Latency
- Jitter
- Historical success
- Source quality
- Protocol compatibility
- Endpoint reputation
- Recency
- DNS stability
- Chain complexity

- Score formula documented.
- Score is deterministic.
- Frontend displays confidence buckets.
- Outputs can filter by confidence.
- Tests assert invariants.

#### 5.4 Retest queue and stale cache policy

Retesting every proxy wastes time, but stale cache can lie.

- Retest high-confidence proxies less often.
- Retest flaky proxies more often.
- Retest proxies from changed sources.
- Retest after DNS changes.
- Retest before promoting to chosen output.
- Expire by protocol risk.

- Cache entries include test engine and profile.
- Cache invalidates when parser/output version changes.
- Chosen outputs prefer fresh tests.
- Stale working proxies are marked stale, not silently trusted.
- Retest report is generated.

### 6. Washing, revival, WARP, Vwarp, and smart chains

#### 6.1 Revival lifecycle model

Revived, washed, shielded, candidate, and verified terms must be precise.

##### Proposed lifecycle

1. `native_candidate`
2. `native_validated`
3. `native_tested_working`
4. `native_tested_failed`
5. `wash_candidate`
6. `washed_generated`
7. `washed_tested_failed`
8. `washed_tested_working`
9. `shielded_candidate`
10. `shielded_verified`
11. `smart_chain_candidate`
12. `smart_chain_verified`

1. Add lifecycle enum.
2. Add lifecycle transitions.
3. Add transition tests.
4. Add metadata counts.
5. Update frontend labels.
6. Update output filters.

- Untested generated chains are never counted as working.
- Verified counts require retest evidence.
- Candidates remain available but labeled experimental.
- Frontend and docs use the same terms.
- Metadata includes lifecycle breakdown.

#### 6.2 Smart chain planner v2

Chains should be built intentionally, not just combined.

##### Planner inputs

- Protocol compatibility
- Latency
- Country/region
- ASN diversity
- Source diversity
- Failure history
- Endpoint type
- DNS-safe availability
- WARP/Vwarp availability
- User profile: speed, stealth, reliability

##### Chain types

- Direct fallback
- Relay chain
- WARP wrapped
- Vwarp MASQUE
- Vwarp AtomicNoize
- Double WARP
- Local proxy + WARP
- CDN worker chain
- Custom user chain

1. Define chain strategy objects.
2. Add compatibility rules.
3. Add cost model.
4. Add chain score.
5. Add chain validation before output.
6. Add retest for verified chains.
7. Add lab visualization.

- No loops in chain graph.
- No invalid detours.
- No duplicate tags.
- Chain score is explainable.
- Strategy-specific tests exist.
- Output validator checks chain references.

#### 6.3 Chain simulation before testing

Some invalid chains can be caught without running network tests.

##### Simulate

- Outbound graph shape
- Tag uniqueness
- Detour existence
- Selector references
- Unsupported client fields
- Missing keys
- Private endpoints
- Protocol/client incompatibility
- DNS detour correctness

- Simulator catches broken Sing-box references.
- Simulator catches broken Clash groups.
- Simulator runs in lab before export.
- Simulator errors are user-readable.
- CI uses simulator on generated artifacts.

#### 6.4 WARP key pool management

WARP key handling needs safety, rotation, and observability.

- Key pool health status.
- Per-key failure counters.
- Reserved bytes validation.
- Peer public key validation.
- Rotation policy.
- “No keys configured” degraded mode.
- User-provided key validation in lab.
- Never log full keys.

- Invalid key rejected.
- Missing key produces clear degraded reason.
- Key usage is masked in logs.
- Lab validates format before export.
- Docs explain user-owned keys.

### 7. DNS, evasion profiles, and network hardening

#### 7.1 DNS engine v2

DNS-safe and DNS-hardened outputs are important, but DNS needs its own engine with transparent results.

##### Features

- Async resolver abstraction.
- DoH/DoT/DoQ profile selection.
- Result cache with TTL.
- Resolution confidence.
- DNS poisoning detection heuristics.
- IP-literal rewrite safety.
- SNI/Host preservation.
- Per-protocol rewrite rules.
- Fail-open/fail-safe modes.

- DNS-safe drops unresolved entries by design.
- DNS-hardened keeps unresolved entries with hardened resolvers.
- SNI and Host are preserved.
- Private resolved IPs are blocked where policy requires.
- Resolution failures are counted.
- Docs explain differences.

#### 7.2 Evasion profile system

Users face different network conditions. Profiles should be explicit and testable.

##### Profiles

- `standard`: minimal modifications.
- `dns_hardened`: hardened resolvers.
- `dns_safe`: IP-literal/pre-resolved.
- `stealth`: uTLS/ALPN/mux where supported.
- `aggressive`: stronger evasion and chains.
- `low_latency`: speed-first.
- `high_reliability`: reliability-first.
- `manual_lab`: user-controlled.

1. Define profiles in JSON.
2. Map profile to output variants.
3. Map profile to lab defaults.
4. Add compatibility checks.
5. Add profile-specific output validation.
6. Expose profile in metadata.

- Every profile has docs.
- Unsupported protocol/profile combinations are skipped or warned.
- Frontend shows profile tradeoffs.
- Tests cover each profile.

#### 7.3 Censorship diagnostics without unsafe scanning

The lab can help users understand their own network without automatically scanning third parties.

##### Safe diagnostics

- Browser reachability to same-origin assets.
- DNS resolver availability.
- User-entered endpoint test.
- Local proxy detection.
- Captive portal hint.
- Clock skew check.
- IPv4/IPv6 availability.
- WebSocket reachability to user-provided endpoint.
- Manual clean-IP import.

##### Rules

- No automatic broad IP scans.
- No hidden third-party requests.
- No default active probing of random hosts.
- User must initiate external tests.
- Clearly label what will be contacted.

- Every diagnostic explains network contact.
- Offline mode never contacts network.
- Online mode asks before external tests.
- Results are stored locally unless user exports.
- Docs include safety boundary.

### 8. Output generation and public artifacts

#### 8.1 Output transaction system

Outputs should be written atomically as a complete transaction.

- Generate into `output.tmp/<trace_id>/`.
- Validate all outputs.
- Write manifest.
- Promote directory atomically.
- Keep previous good snapshot.
- Mark degraded snapshot clearly.
- Never mix old/new files.

- Partial writes never publish.
- Previous known good snapshot retained.
- Manifest represents exact promoted files.
- Failed validation blocks promotion or marks degraded.
- Tests simulate failure mid-write.

#### 8.2 Output family expansion

##### Potential output families

- Sing-box standard
- Sing-box VPN/TUN
- Sing-box chains
- Clash/Mihomo
- Base64 universal
- Plain URI list
- Per-protocol URI files
- Per-country files
- DNS-safe variants
- DNS-hardened variants
- Shadowrocket
- Surge
- Loon
- Quantumult X
- SIP008
- Hiddify import bundle
- NekoBox/NekoRay bundle
- V2RayN/V2RayNG bundle
- OpenVPN side products
- WireGuard side products
- Lab strategy exports
- Debug summary
- Health/control files
- API aliases
- Client compatibility report

##### Instructions

1. Add each output to `docs/output_matrix.json`.
2. Add generator.
3. Add validator.
4. Add docs table generation.
5. Add frontend download card.
6. Add smoke test.
7. Add degraded behavior.

- Output exists.
- Output is validated.
- Output is documented.
- Output has client compatibility notes.
- Output is included in manifest.
- Output is included in screenshot/download UI.

#### 8.3 Client compatibility validator

JSON/YAML syntax validation is not enough. Client configs can be syntactically valid but rejected by actual clients.

##### Add optional validators

- `sing-box check`
- `mihomo -t`
- JSON schema where available
- Client-specific linter rules
- Adapter-specific semantic checks

- Native validators are optional.
- Missing binaries skip cleanly.
- CI can run them when available.
- Failures are reported per file.
- Docs show which checks ran.

#### 8.4 Signed output manifests

Consumers need confidence that outputs are produced by the project and not tampered with.

##### What to sign

- `artifact_manifest.json`
- `metadata.json`
- `proxies.json` hash
- critical subscription hashes
- source commit
- run ID
- generated timestamp

1. Add `artifact_manifest.sig`.
2. Add public key distribution.
3. Add frontend verification.
4. Make missing key behavior explicit.
5. Add offline verifier script.
6. Add docs.

- Signature covers manifest.
- Frontend verifies manifest when key exists.
- Verification failure is visible.
- No placeholder public key in deployed artifact.
- Offline verifier works without network.

#### 8.5 Output quality tiers

Users need simple choices.

##### Tiers

- `stable`: recently tested working, high confidence.
- `fast`: low latency.
- `diverse`: region/protocol diversity.
- `experimental`: untested candidates and shielded candidates.
- `revived`: revived/washed only.
- `dns-safe`: DNS-poisoning-resistant.
- `lab`: custom chain experiments.

1. Add tier labels to proxies.
2. Generate tiered outputs.
3. Add UI download filters.
4. Add docs explaining tradeoffs.
5. Add tests ensuring no unverified candidates enter stable tier.

- Stable tier contains only verified working entries.
- Experimental tier is clearly labeled.
- Tiers are counted in metadata.
- UI explains each tier.
- Output matrix lists tiered files.

### 9. Online Laboratory expansion

#### 9.1 Lab project/session model

The lab should become a structured workspace, not just forms.

A local-only lab project object:

```json
{
  "version": 1,
  "created_at": "...",
  "network_profile": {},
  "input_proxy": {},
  "clean_ips": [],
  "strategy": "vwarp-masque",
  "chain_config": {},
  "test_results": [],
  "exports": []
}
```

- Save/load lab projects.
- Import/export project JSON.
- Local browser storage.
- No server required.
- Redact secrets when sharing.

- Project save/load works offline.
- Secrets can be redacted.
- Versioned migration exists.
- Invalid project import fails safely.
- UI shows project state.

#### 9.2 Guided lab wizard

Users should not need to understand all protocols before using the lab.

##### Wizard modes

- “I have a proxy URI”
- “I have WARP key”
- “I only have local proxy”
- “DNS is poisoned”
- “Everything is blocked”
- “I need fastest config”
- “I need most reliable config”
- “I need manual offline config”

1. Ask simple questions.
2. Select strategy automatically.
3. Show why strategy was chosen.
4. Let advanced users override.
5. Export multiple client formats.

- Wizard works without network.
- Wizard never contacts external endpoints silently.
- Strategy choice is explainable.
- Unsupported inputs show helpful errors.
- Docs mirror wizard flow.

#### 9.3 Visual chain builder

Chains are hard to understand. A visual graph makes them clearer.

- Nodes: direct, proxy, WARP, Vwarp, worker, DNS, selector.
- Edges: detour, route, fallback.
- Validation badges.
- Latency/confidence labels.
- Export preview.
- Error highlighting.

1. Build graph model from chain config.
2. Render with accessible HTML/SVG.
3. Validate graph before export.
4. Allow drag/drop only if it preserves valid topology.
5. Add screenshot tests.

- Invalid detours highlighted.
- Missing credentials highlighted.
- Client compatibility shown.
- Graph is keyboard accessible.
- Offline mode works.

#### 9.4 Lab config linter

Before testing or exporting, lint configs locally.

##### Lint checks

- Missing outbound tags.
- Duplicate tags.
- Missing detours.
- Unsupported client fields.
- Private/internal endpoints.
- Empty credentials.
- Invalid UUIDs.
- Invalid ports.
- Unsupported transport/client combination.
- DNS resolver conflicts.
- Placeholder values.

- Linter runs before export.
- Linter messages are actionable.
- Warnings vs errors are distinct.
- Tests cover each lint rule.
- No raw secrets appear in lint logs.

#### 9.5 Lab live-test sandbox

Live tests are valuable but risky. They must be bounded.

- User-visible “this will contact X” confirmation.
- Rate limit.
- Payload size cap.
- Process timeout.
- Allowed outbound types.
- Private/internal endpoint blocking.
- Admin key for hosted production.
- Local-only mode for user machines.
- Test result explanation.

- Production live test disabled by default.
- Static Pages shows manual mode.
- Backend mode requires explicit enablement.
- Live test kills child process on timeout.
- Test results are sanitized.
- Browser UI shows manual fallback.

#### 9.6 Local QR generation

QR export must not send configs to third-party QR services.

1. Vendor a local QR generator.
2. Keep it same-origin.
3. Add no-network browser test.
4. Redact QR preview when secrets hidden.
5. Add offline lab support.

- No external QR API.
- QR works offline.
- Large payload warning exists.
- User can copy raw payload.
- Tests block external requests.

#### 9.7 Lab export pack

One export should create a bundle for the user.

##### Bundle contents

- Sing-box JSON
- Clash YAML
- Xray JSON
- NekoBox/NekoRay link
- URI
- QR payload
- Python runner
- Bash runner
- README
- Troubleshooting guide
- Redacted project file
- Full project file, only if user chooses

- ZIP paths are safe.
- Secrets are included only by explicit user action.
- README explains each file.
- Bundle works offline.
- ZIP scanned for placeholder/deploy secrets.

#### 9.8 Lab result explainability

Users need to understand why something failed.

##### Failure categories

- Invalid input
- Unsupported protocol
- Missing credential
- DNS failure
- Connection timeout
- TLS failure
- Client config invalid
- Local process unavailable
- Live testing disabled
- Private endpoint blocked
- Browser/network limitation

- Every failure has category.
- UI gives next action.
- Advanced details are expandable.
- Error text is escaped.
- Docs include troubleshooting mapping.

### 10. Offline Laboratory expansion

#### 10.1 Fully self-contained offline HTML

A single file should work with no internet, no server, no build step.

##### Include

- CSS
- JS
- Strategy manifest
- Parser helpers
- Config linter
- Local QR generator
- Export builders
- Documentation snippets

- No external fonts.
- No external images.
- No CDN.
- No network fetch.
- No service worker requirement.
- No hidden tracking.

- Opens from `file://`.
- Works with JavaScript enabled.
- Shows clear no-network mode.
- All assets embedded.
- Browser test blocks network and passes.

#### 10.2 Offline CLI wizard

Some users need terminal-only tools.

- Parse URI.
- Validate fields.
- Ask guided questions.
- Build chain.
- Export files.
- Optional local sing-box test.
- No external requests unless user confirms.

- Runs with Python standard library where possible.
- Clear prompts.
- Redacts secrets in logs.
- Can run in no-network mode.
- Produces same strategy outputs as online lab.

#### 10.3 Portable diagnostics bundle

Users in restricted networks may need a portable toolkit.

##### Bundle

- `lab-offline.html`
- `lab-scanner.py`
- `lab-runner.sh`
- Example configs
- Troubleshooting markdown
- Client install notes
- Checksums
- Signature

- Bundle is reproducible.
- Bundle does not include project deploy secrets.
- Scripts explain every network action.
- Checksums published.
- Docs explain offline use.

### 11. Frontend dashboard and UX

#### 11.1 Health-first dashboard

The dashboard should immediately show whether outputs are fresh, degraded, stale, or unverified.

##### Display

- Status: ok/degraded/stale
- Generated at
- Source commit
- Run ID
- Working count
- Tested count
- Confidence distribution
- Degraded reason
- Manifest verification
- Last successful full run
- Output file coverage

- Reads `health.json`.
- Falls back gracefully if missing.
- Shows stale warning.
- Shows degraded warning.
- Does not overstate working counts.
- Screenshot test covers degraded state.

#### 11.2 Output download decision helper

Users should not need to understand every format.

##### Questions

- Which app do you use?
- Do you need VPN/TUN mode?
- Is DNS blocked?
- Do you want fastest or most reliable?
- Are experimental chains okay?
- Do you need offline import?

##### Output

Recommend file(s):

- `singbox.json`
- `singbox-vpn.json`
- `clash.yaml`
- `base64.txt`
- DNS-safe/hardened variant
- side product ZIP
- lab export

- Recommendations map to output matrix.
- Missing outputs are hidden or disabled.
- Degraded outputs show warning.
- App compatibility docs linked.
- No broken links.

#### 11.3 Protocol explorer

Show protocol support honestly.

##### Display per protocol

- Parsed count
- Working count
- Confidence
- Export support
- Client support
- Common failure reasons
- Example import format
- Security notes

- Reads protocol matrix.
- Counts from metadata/proxies.
- Does not claim export support where false.
- Links to docs.
- Browser test verifies filters.

#### 11.4 Source health page

Operators need to know which sources are useful.

- Source health score
- Last fetched
- Fetch failures
- Parse yield
- Working yield
- Duplicate rate
- Protocol mix
- Cooldown state
- Reason for demotion

- Sensitive source URLs are masked or hashed.
- Page can be hidden from public if needed.
- Source report exists.
- Docs explain scoring.
- No secret tokens exposed.

#### 11.5 Accessibility and internationalization

Anti-censorship tools should be usable on low-end devices, screen readers, and multiple languages.

##### Improvements

- Keyboard navigation.
- ARIA labels.
- High-contrast mode.
- Reduced-motion mode.
- RTL language support.
- Offline translation bundles.
- No icon-only actions.
- Clear error messages.

- Lighthouse/accessibility pass.
- Keyboard-only lab flow works.
- RTL screenshots checked.
- No layout overflow on mobile.
- Translation keys validated.

### 12. Performance and efficiency

#### 12.1 Streaming parser pipeline

Avoid loading huge source payloads fully into memory.

1. Stream fetch chunks.
2. Split into bounded line batches.
3. Decode incrementally.
4. Push micro-chunks to parser workers.
5. Apply backpressure.
6. Track dropped chunks.

- Large source memory stays bounded.
- Parser handles line split across chunks.
- Backpressure metrics exist.
- Tests simulate large payload.
- No blocking CPU work in event loop.

#### 12.2 Adaptive concurrency controller

Static concurrency is inefficient. Use feedback from latency, errors, queue depth, CPU, memory, and rate limits.

##### Inputs

- Queue depth
- Fetch latency p50/p95
- Timeout rate
- DNS failure rate
- CPU usage
- Memory usage
- Source host error rate
- Tester availability

1. Add controller per subsystem: fetch, parse, test, DNS.
2. Use conservative AIMD behavior.
3. Cap concurrency per host.
4. Log decisions.
5. Add simulation tests.

- Concurrency decreases under failure.
- Concurrency increases slowly under success.
- Per-host caps enforced.
- No unbounded queue growth.
- Metrics explain throttling.

#### 12.3 Output generation optimization

Generating many variants can duplicate work.

- Cache converted outbounds.
- Reuse DNS-safe/hardened proxy lists.
- Generate adapters from normalized intermediate representation.
- Avoid repeated JSON serialization.
- Parallelize independent output families.
- Use atomic writes.

- No duplicate conversion per proxy.
- Output generation time measured.
- Memory use measured.
- Output hashes stable.
- Tests verify deterministic output.

#### 12.4 Test cache efficiency

Testing is expensive. Cache intelligently.

- Cache by normalized proxy fingerprint.
- Include test profile and engine in key.
- Expire by confidence and age.
- Invalidate on parser/tester version change.
- Store failure reasons.
- Avoid trusting stale failures forever.

- Cache key is stable.
- Cache does not include raw secrets.
- Version changes invalidate relevant entries.
- Stale cache is visible.
- Tests cover hit/miss/expiry.

#### 12.5 CI time-budget optimization

The project is zero-budget and uses GitHub Actions. CI needs to be fast and targeted.

##### Strategy

- Unit tests on every PR.
- Focused integration tests on touched areas.
- Full production-smoke on main/nightly.
- Browser tests split by profile.
- Native validator optional.
- Artifact retention tuned.

- Test profiles documented.
- CI reports skipped browser dependencies loudly.
- Slow tests are marked.
- Coverage is meaningful.
- Artifacts are retained long enough for audits.

### 13. Robustness and degraded modes

#### 13.1 Degraded output contract

No working proxies should not mean no output. It should mean valid degraded output.

##### Degraded states

- `no_sources_fetched`
- `no_proxies_parsed`
- `no_proxies_validated`
- `no_proxies_working`
- `tester_unavailable`
- `dns_resolution_failed`
- `output_partial`
- `deploy_stale_known_good`
- `schema_validation_failed`

1. Define degraded reasons enum.
2. Add to `health.json`.
3. Add frontend warnings.
4. Add deploy policy.
5. Add tests for every degraded state.

- Every degraded state has valid artifacts.
- Users see clear warning.
- No unverified proxies counted as working.
- Deploy only fails on invalid/unsafe artifacts.
- Docs explain degraded behavior.

#### 13.2 Stale-known-good fallback

When a run fails, users may prefer last known good outputs over nothing.

##### Requirements

- Explicitly mark stale.
- Include previous generated timestamp.
- Include current failed run timestamp.
- Include reason stale output reused.
- Keep hashes.
- Never silently mix stale and fresh files.

- Stale state visible in `health.json`.
- Manifest says which files are stale.
- Frontend warns.
- Tests simulate failed run fallback.
- Docs explain freshness.

#### 13.3 Chaos testing

The pipeline should survive hostile conditions.

##### Scenarios

- All sources timeout.
- Half sources return HTML.
- Sources return huge payloads.
- DNS fails.
- Tester binary missing.
- Go tester hangs.
- Python fallback errors.
- WARP key invalid.
- Output write fails.
- Disk full simulation.
- GitHub artifact missing.
- Frontend metadata missing.
- Browser offline.

- Chaos tests are deterministic.
- Each scenario yields valid degraded output or safe failure.
- Logs are sanitized.
- No resource leak.
- Recovery path documented.

### 14. Observability and reports

#### 14.1 Run timeline report

Operators need to know where time was spent.

##### Report sections

- Fetch phase duration
- Parse phase duration
- Validation duration
- Testing duration
- Washing duration
- DNS output duration
- Output writing duration
- Validation duration
- Deploy duration
- Bottlenecks
- Top slow sources
- Top failure categories

- Timeline report generated.
- No secrets in report.
- Included in artifact bundle.
- Frontend can render summary.
- CI uploads report.

#### 14.2 Failure taxonomy

Failure messages should be consistent and aggregatable.

##### Categories

- `fetch_timeout`
- `fetch_http_error`
- `fetch_policy_block`
- `parse_malformed`
- `validation_missing_credential`
- `validation_private_ip`
- `test_timeout`
- `test_tls_error`
- `test_dns_error`
- `output_schema_error`
- `deploy_missing_artifact`
- `frontend_placeholder_error`

- Failure reasons are enums.
- Metrics use enums, not free text.
- Docs explain reasons.
- Frontend maps reasons to user text.
- Tests assert known categories.

#### 14.3 Operator debug bundle

When something goes wrong, the maintainer should download one safe bundle.

##### Contents

- Sanitized logs
- `health.json`
- `metadata.json`
- `artifact_manifest.json`
- Run timeline
- Source quality report
- Failure taxonomy summary
- Test engine summary
- Output validator report
- Screenshots
- Environment summary with secrets redacted

- Bundle has safe paths.
- Bundle is ZIP validated.
- Secrets redacted.
- Size bounded.
- Generated only when enabled or in CI.

### 15. APIs and data contracts

#### 15.1 Versioned public API

Public consumers need stable contracts.

##### Add

- `/api/v1/stats`
- `/api/v1/proxies`
- `/api/v1/health`
- `/api/v1/manifest`
- `/api/v1/protocols`
- `/api/v1/outputs`
- `/api/v1/diff/proxies`

- Existing aliases remain or redirect.
- API version documented.
- Schema files exist.
- Contract tests cover API.
- Breaking changes require version bump.

#### 15.2 Snapshot identity and diffs

`base_version` must map to a real snapshot, not just a string.

- Snapshot ID equals manifest hash or generated timestamp + commit.
- Store previous snapshot metadata.
- Diffs only if base snapshot known.
- Otherwise return full reload required.
- Include target version.

- Unknown base version does not produce fake diff.
- Known version produces correct added/removed.
- Snapshot store is bounded.
- Docs explain diff behavior.

#### 15.3 Schema evolution policy

As metadata grows, schemas must evolve safely.

- Additive changes are minor.
- Breaking changes bump schema major.
- Frontend supports at least current and previous schema.
- Unknown keys policy is explicit.
- Generated docs list schema fields.

- Schema version included.
- Validators enforce required fields.
- Frontend handles missing optional fields.
- Migration tests exist.
- Changelog notes schema changes.

### 16. Online/offline output verification

#### 16.1 Browser output verifier

Users should be able to verify downloaded artifacts locally.

- Upload or fetch manifest.
- Verify hashes.
- Verify signature.
- Show file coverage.
- Show stale/degraded state.
- Work offline if files are provided.

- No external network required for local verification.
- Signature failures visible.
- Hash mismatch visible.
- Large file handling safe.
- Docs explain verification.

#### 16.2 Native config dry-run helper

Users should know if a config is accepted by their client before using it.

- Browser-only structural validation.
- Local CLI validation using sing-box/mihomo if installed.
- Offline lab instructions.

- Browser validation never claims full native compatibility.
- Native validation output is parsed and explained.
- Missing binary gives instructions.
- Tests cover missing/invalid/valid cases.

### 17. Security, privacy, and abuse prevention

#### 17.1 Threat model refresh

Project capabilities grew. Threat model must cover current and future risks.

##### Threats

- Malicious sources
- Secret leakage
- Public artifact tampering
- WebSocket resource exhaustion
- Dependency compromise
- Zip slip
- Placeholder key deployment
- Output poisoning
- Stale artifact trust

- SECURITY.md updated.
- Each threat has mitigation.
- Tests map to threats.
- Residual risks listed.
- User safety notes included.

#### 17.2 Lab abuse controls

The online lab can run tests and generate configs. 

##### Controls

- Production disabled by default.
- Allowlisted outbound types.
- Private/internal endpoint blocks.
- Timeout and process cleanup.

- Controls enforced server-side.
- Frontend labels mode.
- Static Pages cannot run live tests.
- Logs sanitized.

#### 17.3 Dependency and supply-chain hardening

Proxy tooling is dependency-heavy. Supply chain must be controlled.

- Dependency lock with hashes.
- Scheduled dependency audit.
- License check.
- SBOM generation.
- Binary checksum pinning.
- Release attestations.
- Vendored frontend asset manifest.
- No runtime CDN.

- Lock file generated.
- Audit failures triaged.
- Binary downloads checksum-verified.
- SBOM attached to releases.
- Frontend assets have source manifest.
- Docs explain reproducibility.

### 18. DevOps, CI/CD, releases, and mirrors

#### 18.1 Separate software release and data release

Software releases and proxy output releases are different.

##### Software release

- Tagged version.
- Python package.
- Native binaries.
- Docker image.
- Attestations.
- Changelog.

##### Data release

- Scheduled pipeline output.
- Pages artifact.
- Manifest.
- Health.
- Subscriptions.
- Lab/public files.

- Two workflows documented separately.
- Two readiness gates.
- No data-output failure blocks software release unless intended.
- No software-release claim implies fresh proxy outputs.
- Status page shows both.

#### 18.2 Longer latest-output retention

A 3-day artifact retention window is weak for auditability.

##### Options

- Increase Actions artifact retention.
- Publish sanitized latest-output evidence bundle.
- Store run summaries in GitHub Releases.
- Store manifest history in Pages.
- Keep rolling N manifests.

- Latest output can be audited after a week/month.
- Sensitive files excluded.
- Storage stays zero-budget.
- Manifest history bounded.
- Docs explain retention.

#### 18.3 Deploy smoke tests

Local validation is not enough. Test the deployed site.

##### Smoke checks

- `index.html` loads.
- `health.json` loads.
- `metadata.json` fresh.
- `artifact_manifest.json` valid.
- `api/proxies` equals `proxies.json`.
- `api/stats` equals `metadata.json`.
- `base64.txt` decodes or is valid empty degraded.
- Frontend no placeholders.
- Lab page static/manual mode correct.
- No external runtime requests.

- Smoke runs after Pages deploy.
- Failure creates visible issue/artifact.
- Screenshots saved.
- Hash mismatches fail.
- Stale site detected.

#### 18.4 Optional mirror parity

Mirrors are useful only if users can trust them.

##### Mirrors

- GitHub Pages
- IPFS/IPNS
- Hugging Face
- Google Drive
- Telegram
- Vercel/Netlify optional frontend mirrors

- Mirror is optional.
- Mirror uses same manifest.
- Mirror hash parity checked.
- Mirror failure does not break core.
- Frontend labels mirror freshness.
- Docs explain trust model.

### 19. Testing strategy expansion

#### 19.1 Test profile maturity

- `unit`
- `integration`
- `frontend-browser`
- `frontend-no-network`
- `frontend-degraded`
- `production-smoke`
- `output-contract`
- `protocol-golden`
- `security`
- `chaos`
- `performance`
- `release`

- Each profile documented.
- CI uses appropriate profiles.
- Local developer can run fast subset.
- Full gate runs before production claim.
- Skips are visible and explained.

#### 19.2 Visual regression testing

Frontend and lab changes need screenshot proof.

##### Screenshots

- Home dashboard ok.
- Home dashboard degraded.
- Proxies page.
- Analytics page.
- Lab wizard.
- Lab manual mode.
- Lab live mode.
- Offline lab.
- Mobile viewport.
- RTL language.

- Screenshots generated in CI.
- Differences reviewed.
- Secrets redacted.
- Broken layout fails test.
- Images archived with run.

#### 19.3 Golden output fixtures

Generated config regressions are hard to see.

##### Fixtures

- One fixture per protocol.
- One fixture per output family.
- One fixture per DNS mode.
- One degraded fixture.
- One zero-working fixture.
- One chain fixture.
- One side-product ZIP fixture.

- Golden fixtures deterministic.
- Sensitive values synthetic.
- Format validators run.
- Client semantic validators optional.
- Matrix claims backed by fixture.

### 20. Analytics and intelligence

#### 20.1 Proxy history intelligence

Use history to improve output quality.

- Uptime over time
- Latency trend
- Jitter trend
- Failure streak
- Protocol stability
- Region stability
- Source reliability
- Revival success
- DNS stability

##### Uses

- Better ranking
- Better chosen outputs
- Better retest scheduling
- Better source scoring
- Better user recommendations

- History DB bounded.
- Privacy preserved.
- Ranking formula documented.
- Tests cover ranking invariants.
- Frontend shows trend summaries.

#### 20.2 Recommendation engine

Users want “best for me,” not raw lists.

##### Recommendation profiles

- Fastest
- Most reliable
- Best for mobile
- Best for desktop
- DNS-block resistant
- Experimental bypass
- Low battery
- Low data usage
- High privacy

1. Define recommendation profiles.
2. Map profiles to output tiers.
3. Add frontend wizard.
4. Add lab strategy suggestions.
5. Explain why each recommendation was made.

- Recommendations are transparent.
- No untested proxy recommended as stable.
- User can override.
- Tests check profile selection.
- Docs explain ranking.

#### 20.3 Source discovery suggestions

Help maintainers improve source lists without blindly adding noise.

- Detect dead sources.
- Suggest replacements from manual input.
- Score candidate sources in probation.
- Identify duplicate sources.
- Identify sources with unique protocols.
- Generate review report.

##### Safety

Do not scrape the web automatically for sources unless explicitly configured and policy-reviewed.

- Suggestions are reports, not auto-adds.
- New sources get probation.
- Duplicate sources detected.
- Maintainer review required.
- Source provenance documented.

### 21. Documentation and governance

#### 21.1 Generated docs from matrices

Avoid docs drift.

##### Generate from

- Capability registry
- Protocol matrix
- Output matrix
- Claim ledger
- Module ownership map
- Environment variable schema

- README tables generated.
- API docs generated.
- Lab strategy docs generated.
- Manual edits blocked in generated blocks.
- CI checks generated docs are current.

#### 21.2 Decision records

Major choices need permanent explanations.

##### Create ADRs for

- Raw static frontend vs Vite.
- DNS-safe vs DNS-hardened semantics.
- Shielded candidate accounting.
- Source scheduler behavior.
- Live lab production policy.
- Optional mirrors.
- Strict vs compatibility parser mode.
- Active scanning boundary.

- ADR template exists.
- Each major decision linked from docs.
- Superseded ADRs marked.
- Status matches implementation.
- Changelog references ADRs.

#### 21.3 User-facing troubleshooting tree

Users need simple fixes.

##### Troubleshooting categories

- Subscription empty.
- App rejects config.
- DNS blocked.
- Proxies slow.
- All proxies fail.
- Lab live test unavailable.
- QR too large.
- WARP key invalid.
- Static Pages stale.
- Browser cache stale.

- Each issue has symptoms.
- Each issue has cause.
- Each issue has next action.
- Links to relevant output.
- Available offline.

### 22. Backend API/server enhancements

#### 22.1 Health endpoints by subsystem

- `/health`
- `/health/outputs`
- `/health/tester`
- `/health/lab`
- `/health/frontend`
- `/health/dependencies`

- No secrets exposed.
- Status values consistent.
- JSON schema documented.
- Frontend consumes public-safe subset.
- Tests cover missing output state.

#### 22.2 Admin API hardening

- Key rotation support.
- Request ID.
- Audit log.
- Rate limit per endpoint.
- Optional HMAC-signed payload.
- Local-only admin mode.

- Production requires auth.
- Bad keys fail constant-time.
- Admin audit logs sanitized.
- Docs explain deployment.
- Tests cover auth matrix.

#### 22.3 WebSocket event stream v2

Push update events and health changes to frontend clients safely.

- Heartbeat.
- Idle timeout.
- Max connections.
- Backpressure queue.
- Event type allowlist.
- Last-event replay.
- Connection stats.

- One slow client cannot block broadcast.
- Messages are bounded.
- Unknown client messages ignored safely.
- Tests simulate disconnects.
- Frontend reconnects cleanly.

### 23. Data model and storage

#### 23.1 Normalize internal proxy model

Ensure every proxy has consistent fields.

- Canonical endpoint object.
- Credentials object.
- Transport object.
- TLS object.
- Test result object.
- Provenance object.
- Output compatibility object.

- Backward compatibility handled.
- Serialization schema updated.
- Parsers map into normalized model.
- Converters consume normalized model.
- Tests cover round-trip.

#### 23.2 Storage cleanup and retention

History/cache databases can grow.

- Retention policy.
- Vacuum/compact.
- Max rows per table.
- Export summaries.
- Corruption recovery.
- Backup/restore.

- DB size bounded.
- Corruption does not crash pipeline.
- Recovery path tested.
- Retention documented.
- Metrics show storage size.

### 24. Expansion features for users

#### 24.1 Personal profile generator

Generate outputs tailored to user constraints.

- Client app
- Country/region preference
- Latency preference
- DNS situation
- Protocol preference
- Experimental allowed
- Battery/data constraints

##### Outputs

- Recommended subscription
- Lab strategy
- Explanation
- Fallback plan

- Runs client-side where possible.
- Does not upload preferences.
- Profiles can be exported.
- No secrets stored without consent.
- Docs explain privacy.

#### 24.2 BYOW improvements

Bring Your Own Worker can be powerful but must be guided.

- Worker URL validation.
- Deployment guide.
- Config generator.
- Security warnings.
- Local-only storage.
- Health check.
- Export to supported clients.

- Worker URL sanitized.
- No credentials leaked.
- Docs explain Cloudflare limits.
- Lab integrates worker strategy.
- Tests cover invalid URL/XSS.

#### 24.3 Community source contribution flow

Let contributors add sources safely.

##### Flow

1. Submit source object.
2. Validate URL policy.
3. Run probation fetch.
4. Compute parse yield.
5. Check duplicate rate.
6. Check security drops.
7. Generate source review report.
8. Maintainer approves.

- PR template exists.
- CI validates source object.
- New source starts disabled/probation if needed.
- No tokenized private URLs allowed.
- Source docs updated.

### 25. Performance benchmarks

#### 25.1 Benchmark suite

Track speed regressions.

##### Benchmarks

- Parse 10k mixed lines.
- Deduplicate 100k proxies.
- Generate outputs for 10k proxies.
- Validate Pages artifact.
- DNS-safe rewrite for 10k proxies.
- Go tester batch overhead.
- Python fallback overhead.
- Frontend render 5k proxies.
- Lab config lint.

- Benchmarks deterministic.
- CI records trend.
- Thresholds avoid flakiness.
- Results saved as artifact.
- Regressions require explanation.

#### 25.2 Memory profiling

Large runs can OOM.

- Peak memory tracking.
- Per-phase memory.
- Large fixture tests.
- Streaming assertions.
- Memory leak tests for repeated runs.

- Peak memory reported.
- Large payload test passes.
- Repeated mini-runs do not leak significantly.
- Output generation memory bounded.
- Docs include tuning knobs.

### 26. Final recommended build order

#### Wave 1: Truth and contracts

1. Capability registry.
2. Module ownership map.
3. Docs hierarchy cleanup.
4. Output/release policy unification.
5. Durable latest-output evidence bundle.
6. Deploy smoke tests.

#### Wave 2: Pipeline correctness

1. Source provider abstraction.
2. Source quality v2.
3. Parser result contract.
4. Failure taxonomy.
5. Multi-stage validation.
6. Degraded state enum.

#### Wave 3: Quality and intelligence

1. Tester capabilities.
2. Confidence scoring.
3. Retest scheduler.
4. History intelligence.
5. Recommendation profiles.
6. Source scheduler.

#### Wave 4: Labs

1. Lab project model.
2. Guided wizard.
3. Config linter.
4. Visual chain builder.
5. Offline HTML.
6. Export pack.
7. Local QR generation.

#### Wave 5: Outputs

1. Output transaction system.
2. Client compatibility validator.
3. Signed manifests.
4. Tiered outputs.
5. Expanded adapter support.
6. Public verifier.

#### Wave 6: Performance and robustness

1. Streaming parser pipeline.
2. Adaptive concurrency.
3. Output generation optimization.
4. Chaos tests.
5. Memory benchmarks.
6. CI profile optimization.

#### Wave 7: Security and release maturity

1. Fetch DNS rebinding protection.
2. Threat model refresh.
3. Admin API v2.
4. Supply-chain hardening.
5. Software/data release separation.
6. Mirror parity verification.

### 27. Master checklist for declaring a feature “complete”

A feature is complete only when all applicable boxes are checked:

- Implementation merged.
- Feature flag/default chosen.
- Unit tests added.
- Integration tests added.
- Degraded-mode tests added.
- Security tests added.
- Frontend tests added, if UI touched.
- Visual screenshot added, if UI touched.
- Output validator updated, if artifact touched.
- Protocol matrix updated, if protocol touched.
- Output matrix updated, if public file touched.
- Capability registry updated.
- Claim ledger updated only if proof exists.
- README updated.
- Wiki updated.
- STATUS updated.
- CHANGELOG updated.
- SECURITY updated, if risk changed.
- No raw secrets in logs or artifacts.
- No placeholder leakage.
- No stale docs with old behavior.
- Public/deploy smoke passes, if public surface touched.
- Rollback path documented.

### 28. Highest-value next enhancements

The most valuable improvements are:

1. **Capability registry** - prevents future overclaims.
2. **Durable latest-output evidence bundle** - makes every run auditable.
3. **Lab project model + linter** - dramatically improves online/offline lab usefulness.
4. **Confidence scoring** - improves user trust more than raw proxy counts.
5. **Source quality v2** - improves pipeline efficiency and output quality.
6. **Output transaction system** - prevents mixed/stale artifacts.
7. **Signed manifests + browser verifier** - improves public artifact trust.
8. **Deploy smoke with screenshots** - closes the gap between local tests and real user experience.
9. **Adaptive scheduler/concurrency** - saves CI time and improves resilience.
10. **Documentation generation from matrices** - prevents drift from returning.

The guiding principle: **do not expand by adding isolated features; expand by adding capability contracts, proof, safety boundaries, and user-facing explanations with every feature.**
