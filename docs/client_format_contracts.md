# Client Format Artifact Contracts

Release availability policy requires at least 70% usable-source coverage and permits tester infrastructure errors up to 5% of attempted tests only when tested and working counts are positive. Native client validation, nonempty working output, artifact integrity, and source-admission protections still apply. Timing-based resharding requires observations for at least 50% of runtime sources and unambiguous canonical mapping for at least 80% of observed identities. Invalid or non-finite threshold overrides are rejected.

ConfigStream validates generated client artifacts at the GitHub Pages release boundary. These checks are compatibility contracts: generators, finalisation, the output matrix, schemas, tests, documentation, and deployment validation must agree on the same public shapes.

## Public artifact boundary

Public artifacts contain only client-consumable configuration and documented release metadata. Internal tester diagnostics, temporary execution state, secrets, deployment placeholders, and private validation details must not be published.

`metadata.json` exposes structured `record_semantics`; consumers must treat it as an object described by `schema/metadata.schema.json`, not as an opaque scalar. The authoritative machine-readable artifact inventory is `docs/output_matrix.json`, and implementation status is tracked in `docs/core_compatibility_report.json`.

Merged metadata also reports `usable_sources` (sources producing accepted records) and
`transport_success_sources` (successful source fetches). These optional, nonnegative
integer counters are distinct: a successful fetch need not contain usable records.
Source coverage uses usable records; HTTP success must not inflate release coverage.

The Python native connectivity path writes a loopback HTTP inbound using the same
port passed to `singbox2proxy` for readiness checks. A custom config with an
independently assigned inbound port cannot satisfy that wrapper contract. Go
chain payloads may already contain the `direct` outbound used by DNS; the tester
must reuse it instead of adding a duplicate tag. Once the custom-chain circuit
breaker opens, further revival candidates remain unverified and recovery stops
for that tester lifecycle. Intake shutdown also prevents new optional revival
work while consumers drain their queues.

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

Fixtures and regression tests exercise valid and invalid endpoint references, selector fallback, Mihomo chaining, Xray structure, subscription parity, metadata schema compliance, public sanitisation, and complete generated Pages artifacts. The pre-fix CI runs demonstrated the previous contract mismatches; the repair-focused suite passes only after the generator, validator, fixture, matrix, and documentation assumptions are aligned.


### HTTP authentication and native fallback lifecycle

Generic HTTP, HTTPS, SOCKS, Naive, Trojan, TUIC and shared URL parsers decode URI
credentials exactly once. Explicit port zero is invalid; only an omitted port
uses a protocol default. HTTP and HTTPS Clash exports preserve credentials and
TLS, with certificate verification enabled by default, matching the
[Mihomo HTTP contract](https://wiki.metacubex.one/en/config/proxies/http/).

Python fallback wraps HTTP CONNECT with a verified proxy TLS context for HTTPS.
Startup workers own their temporary configs until construction returns, including
when the caller times out or is cancelled. A late process is stopped instead of
being orphaned. The intake deadline ends when producer/consumer work completes;
output generation cannot retroactively mark that work time-limited.
