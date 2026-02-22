# Roadmap Update Process (Living Governance)

This document defines how ConfigStream's roadmap stays synchronized with execution reality.

## Source of Truth

- **Primary planning board:** GitHub Projects (`ConfigStream Roadmap`)
- **Code truth:** merged PRs in `main`
- **Release truth:** tagged releases and workflow attestations

Roadmap entries are only considered complete when all three are aligned.

## Weekly Update Loop

Run this every week (or after any major merge train):

1. Export open and closed roadmap items from GitHub Projects.
2. Reconcile each item with merged PRs and test evidence.
3. Update docs:
   - `docs/ROADMAP.md` status lines
   - `docs/DEBT_MATRIX.md` summary
   - `README.md` operational deltas
4. Publish a short changelog note in the next release.

## Automation Hooks

- CI runs `scripts/generate_debt_matrix.py` for debt visibility.
- CI enforces schema/tests/linting gates before release.
- Release workflow publishes attestations for Python and native artifacts.

## Definition of Done for Roadmap Items

An item is done only when:

- Implementation is merged.
- Tests exist for the new behavior (or explicit rationale is documented).
- Documentation reflects user-facing behavior and limits.
- Security and operational implications are recorded.

## 2027 Expansion Vectors (Tracked)

- Broader edge autonomy (multi-provider edge parity and decentralized mirrors).
- WASM verifier progression from transport-level checks to deeper protocol parity.
- Adaptive recommendation systems with strict rollback and audit controls.
- Additional reproducibility controls for supply-chain hardening.
