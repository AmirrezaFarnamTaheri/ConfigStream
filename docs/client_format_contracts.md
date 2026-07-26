# Client Format Artifact Contracts

ConfigStream validates generated client artifacts at the GitHub Pages release boundary. These checks are compatibility contracts: generators, finalisation, the output matrix, schemas, tests, documentation, and deployment validation must agree on the same public shapes.

## Public artifact boundary

Public artifacts contain only client-consumable configuration and documented release metadata. Internal tester diagnostics, temporary execution state, secrets, deployment placeholders, and private validation details must not be published.

`metadata.json` exposes structured `record_semantics`; consumers must treat it as an object described by `schema/metadata.schema.json`, not as an opaque scalar. The authoritative machine-readable artifact inventory is `docs/output_matrix.json`, and implementation status is tracked in `docs/core_compatibility_report.json`.

## Sing-box

Sing-box validation covers both top-level `outbounds` and top-level `endpoints`, including unique tags, endpoint/outbound detours, selector and URL-test membership, route targets, and DNS detours. Diagnostics distinguish unknown endpoint detours from unknown outbound detours.

When finalisation removes every stale selector or URL-test member, the group falls back to `direct` when that built-in outbound is available. This prevents an emitted selector from becoming structurally empty.

## Mihomo

Mihomo output uses `dialer-proxy` for supported proxy chaining and does not emit deprecated `relay` proxy groups. Validation checks `dialer-proxy` references, proxy-group members, routing-policy references, and required WireGuard fields.

Downstream consumers should expect revived relay-plus-WireGuard chains to be represented as normal proxies linked through `dialer-proxy`, with the WireGuard proxy selected as the usable chain endpoint.

## Xray

`xray.json` is a first-class full configuration artifact. It must contain a non-empty `outbounds` list with unique tags, modern flat VMess/VLESS settings, valid proxy-chain references, and valid routing references. Built-in `direct` and `block` outbounds remain available for routing rules.

The Pages validator performs structural checks before optional native-client validation. The output matrix identifies `xray.json` with `core_format: xray`, and the compatibility report must explicitly record Xray implementation status.

## NekoBox and v2rayN subscriptions

Plaintext subscription files and their Base64 counterparts are contract pairs:

- `proxies.txt` and `base64.txt`
- `proxies-dns-safe.txt` and `base64-dns-safe.txt`
- `proxies-dns-hardened.txt` and `base64-dns-hardened.txt`

Each plaintext file must be valid UTF-8 and contain syntactically valid share-link schemes. Each Base64 file must decode as UTF-8 and match its paired plaintext file exactly. Empty paired files are valid when no usable subscription lines are available.

## Compatibility and regression evidence

Fixtures and regression tests exercise valid and invalid endpoint references, selector fallback, Mihomo chaining, Xray structure, subscription parity, metadata schema compliance, public sanitisation, and complete generated Pages artifacts. The pre-fix CI runs demonstrated the previous contract mismatches; the repaired focused suite passes only after the generator, validator, fixture, matrix, and documentation assumptions are aligned.