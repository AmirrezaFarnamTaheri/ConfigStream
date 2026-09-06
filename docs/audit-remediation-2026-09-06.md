# Repository-wide remediation audit — 2026-09-06

This document tracks the repository-wide remediation associated with GitHub Actions run `34007581775` and the post-merge audit of commit `a669a410f460094cce0caa95126e95fba31606dc`.

The audit covers every tracked first-party code/configuration/workflow/test/documentation surface and the supplied runtime artifacts. Fixes are intentionally landed in focused commits so runtime correctness, scheduling, release integrity, telemetry, persistence/tooling, and workflow hardening can be reviewed independently.

## Confirmed remediation areas

- Go tester shared-daemon IPC ownership/backpressure and lifecycle isolation.
- Infrastructure-failure provenance through Python fallback.
- Runtime source inventory consistency across sharding, admission, timing, resharding, lineage, and release coverage.
- Timing-coverage denominator and censored/unknown timing treatment.
- Timing-aware balancing of the actual 102 runtime parts.
- `STRICT_SECURITY` production wiring.
- GeoIP provisioning/accounting and missing-database semantics.
- sing-box compatibility/version contract alignment.
- History bulk-query correctness and scalability.
- `apply_reshard.py` exact-set safety and failed-run artifact selection.
- Workflow least privilege and repository governance checks that can be enforced in source.
- Cross-layer regression coverage for all of the above.

Additional findings discovered by the expanded all-files sweep will be added to the PR and fixed before the branch is marked ready for review.
