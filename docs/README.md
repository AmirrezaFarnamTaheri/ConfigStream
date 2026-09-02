# Documentation index

ConfigStream keeps active documentation separate from point-in-time review artifacts.

## Maintained guides

- [`DEPLOYMENT.md`](DEPLOYMENT.md): deployment and release operations.
- [`CENSORSHIP_EVASION.md`](CENSORSHIP_EVASION.md): evasion modes and user-facing behavior.
- [`CONFIG_FORGE.md`](CONFIG_FORGE.md): Vwarp configuration reference used by the implementation.
- [`client_format_contracts.md`](client_format_contracts.md): public client artifact contracts.
- [`MODULE_OWNERSHIP.md`](MODULE_OWNERSHIP.md): human-readable ownership map.
- [`../DESIGN.md`](../DESIGN.md): target-state design tokens, visual architecture, and anti-slop guidelines.
- [`../interface-design.md`](../interface-design.md): target-state interface and accessibility specification.
- [`wiki/`](wiki/): product, engineering, protocol, security, and user documentation.

## Machine-readable contracts and generated evidence

- `readiness.json`, `capability_registry.json`, `claim_ledger.json`, and `module_ownership.json` define current project truth.
- `output_matrix.json`, `protocol_matrix.json`, and `core_compatibility_report.json` define public format support.
- `debt_matrix.json`, `DEBT_MATRIX.md`, `maturity_tiers.json`, and `generated/` contain reproducible evidence produced by repository scripts.

## Review artifacts

Point-in-time audits do not belong at the top level of `docs/`. Keep current review evidence in dated `docs/audits/<topic>-YYYY-MM-DD/` directories when it must be versioned, or deliver it outside the source tree. Current release decisions must be reflected in the machine-readable contracts above rather than in a standalone narrative ledger.
