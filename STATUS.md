# ConfigStream Project Status

**Last updated:** 2026-07-12  
**Version:** v3.1.0  
**Current verdict:** **FAIL — release blocked**  
**Active remediation:** [PR #510](https://github.com/AmirrezaFarnamTaheri/ConfigStream/pull/510)

The machine-readable release gate is [`docs/readiness.json`](docs/readiness.json). It is authoritative for current readiness. Historical audit reports and prior “production-ready” wording are provenance only and cannot close a gate.

## Why the gate is blocked

PR #510 implements the Critical and High-priority remediation architecture, but the repository must not be called production-ready until all of the following are directly proven on the final merged commit:

1. The complete CI, security, typing, browser, native, dependency, and pipeline checks are green.
2. A run-scoped pipeline artifact is generated from one source SHA and one container image digest.
3. The artifact contains non-zero tested and working evidence.
4. The artifact contains no private cache/database/log state and no secret material.
5. Every file matches the content-addressed release manifest.
6. The release has not expired.
7. GitHub Pages deploys the exact sealed artifact without rebuilding or mutation.
8. The live Pages smoke and digest-parity checks pass.
9. Historical source-token and proxy-credential exposure has been investigated and affected credentials rotated.

## Remediation implemented on PR #510

| Area | Current state |
|---|---|
| Public serialization | Raw source URLs, internal keys, credentials, request metadata, and raw payloads are removed through an explicit public DTO boundary. |
| Public/private filesystem boundary | The broad `/output` mount is removed; only approved root files are served. Private state is purged before release sealing. |
| Pipeline failure semantics | Production defaults are fail-closed. Zero tested or zero working evidence prevents final release creation. |
| Resource safety | Response, decode, line, source, queue, worker, and deduplication limits are finite and validated. |
| Source provenance | External sources require canonical ownership, full commit/blob identity, bounded acquisition, content digest, timestamp, expiry, and license policy. |
| Stale mirror handling | `rolandmccarthy13/free-proxy-list` is explicitly blocked as a stale ownership-ambiguous mirror. |
| Validation truth | Candidate observations and validation evidence are typed, immutable, expiring, and channel-specific. Stable eligibility requires multi-vantage and longitudinal evidence. |
| State persistence | Quality state is transactional, schema-versioned, fail-loud, and idempotent across replayed runs and shard merges. |
| Telemetry | Event persistence uses a bounded queue and reports drops and shutdown failures. Telemetry is private operational state, not a public web artifact. |
| Live lab | Production live tests require a Bearer credential and literal globally routable IP destinations, eliminating DNS-rebinding re-resolution. |
| Runtime provenance | Shards execute an exact image digest and record source SHA plus image digest. Shared application-state caches and merged artifact paths are removed. |
| Deployment | Pages and mirrors consume one exact successful run artifact, verify expiry and content hashes, and do not rebuild the bundle. |
| Retest | A retest is an immutable child of one exact parent release and records the parent release digest. |
| Tagged releases | Build tools are pinned, mutable AppImage tooling is removed, platform outputs are mandatory, and artifact names no longer make false architecture claims. |
| Documentation claims | Package maturity is Beta until the machine-verifiable release gate passes. |

## Current public-output contract

- A failed, indeterminate, zero-tested, or zero-working run is **not publishable**.
- `proxies.json` and `metadata.json` are required and must be non-empty and internally consistent.
- Runtime caches, SQLite databases, logs, fingerprints, raw source material, and telemetry are private.
- Public files are hashed before `release_manifest.json` is written.
- No public file may change after sealing.
- Every release includes generation time, expiry, source commit, workflow commit, image digest, policy digest, artifact hashes, and optional parent release identity.
- Deployments must reject expired, incomplete, substituted, or mixed-revision artifacts.

## Operator actions required before release

1. Set exact repository variables:
   - `PYTHON_BUILD_VERSION`
   - `PYINSTALLER_VERSION`
   - `VERCEL_CLI_VERSION`
   - `NETLIFY_CLI_VERSION`
   - `PINATA_CLI_VERSION`
2. Review and rotate source tokens or proxy credentials that may have appeared in historical artifacts.
3. Remove or expire affected historical Actions artifacts, releases, Pages builds, mirrors, and IPFS pins where operationally possible.
4. Merge PR #510 only after all blocking checks pass.
5. Run the pipeline from the merged `main` commit.
6. Deploy Pages from that exact successful run.
7. Record the run ID, source SHA, image digest, release ID, Pages deployment ID, and smoke report in `docs/readiness.json`.

## Evidence hierarchy

When claims conflict, use this order:

1. independently reproduced runtime measurement;
2. signed or attested immutable release manifest;
3. exact retained CI artifact;
4. workflow conclusion and machine-readable reports;
5. repository code and configuration;
6. current documentation;
7. historical reports, badges, screenshots, or prose.

No documentation statement may override a failing current gate.
