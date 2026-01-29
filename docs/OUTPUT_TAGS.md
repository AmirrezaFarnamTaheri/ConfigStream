# Output Tagging Format

This document describes the proxy name format (remarks) and the structured
`proxy.tags` emitted by ConfigStream. It is intended to be a complete reference
for every field, value, and transformation rule used in tag output.

## Name (Remarks) Format

Default template:

`{geo} | {stack} | {latency_tag} | {status_tag} | {process_tag} | {issue_tag}`

Each section is optional. Missing parts are removed safely, duplicate
separators are collapsed, and leading/trailing separators are trimmed.

### Template Variables

These placeholders are available to the name template (the default uses a
subset):

- `remarks`: Original proxy name (fallback to `address:port` if empty).
- `protocol`: Uppercased protocol name.
- `stack`: Composite stack label (protocol + transport + security, etc.).
- `transport`: Transport label only (e.g., `WS`, `GRPC`).
- `security`: Security label only (e.g., `TLS`, `REALITY`).
- `status`: `UP` or `DOWN`.
- `status_tag`: Same as `status`.
- `process`: Uppercased process origin (`NATIVE`, `REVIVED-WARP`, etc.).
- `process_tag`: Same as `process`.
- `latency_tag`: `NNNms` string or empty if missing.
- `issue_tag`: `SEC:...` aggregation string or empty.
- `geo`: Flag emoji with optional city suffix.
- `country`: Original country name/code when available.
- `country_code`: ISO 2-letter country code.
- `country_flag`: Flag emoji derived from `country_code`.
- `city`: City name (if available).
- `latency`: Integer latency in ms as a string (no `ms` suffix).
- `asn`: ASN value if known (e.g., `AS15169`).
- `address`: Host/IP used by the proxy.
- `port`: Proxy port.
- `id`: Proxy unique ID (if present).
- `id_short`: First 6 chars of `id` (not used in the default template).

### Section Details

`geo`
- Derived from `country_code`.
- Value is a flag emoji (for example `🇺🇸`) or `🌐` when unknown/invalid.
- If `city` exists, output is `FLAG-City` with spaces converted to `_`
  (for example `🇩🇪-Frankfurt_am_Main`).

`stack`
- Composite label built in this order:
  - `PROTO` (uppercased protocol name; special handling for revived proxies)
  - `TRANSPORT`
  - `SECURITY`
  - `WARP` or `VWARP` (if revived)
  - `METHOD` (for Shadowsocks/SS2022 only)
- Joined by `+`.
- Examples:
  - `VLESS+WS+TLS`
  - `TROJAN+GRPC+REALITY`
  - `SS2022+TCP+AES-256-GCM`
  - `REVIVED-VLESS+WS+TLS+VWARP`

`transport` / transport within `stack`
- Source fields checked in order: `details.net`, `details.type`,
  `details.transport`.
- Normalization mapping:
  - `ws` or `websocket` → `WS`
  - `grpc` → `GRPC`
  - `h2` or `http` → `H2`
  - `tcp` → `TCP`
  - `kcp` → `KCP`
  - `quic` → `QUIC`
  - `udp` → `UDP`
- Default transport if missing:
  - `QUIC` for `hysteria`, `hysteria2`, `tuic`
  - `TCP` otherwise

`security` / security within `stack`
- Derived from `details.security` when present:
  - `reality` → `REALITY`
  - `tls` or `xtls` → `TLS`
- If not present, `TLS` is inferred when `details.tls` is truthy.
- Empty when no TLS/REALITY is detected.

`latency_tag`
- Integer milliseconds with `ms` suffix (e.g., `120ms`).
- Empty if latency is missing or unknown.

`status_tag`
- `UP` when `proxy.is_working` is true.
- `DOWN` otherwise (rare in final outputs).

`process_tag`
- Uppercased `proxy.process` value:
  - `NATIVE` for standard pipeline results
  - `REVIVED-WARP` or `REVIVED-VWARP` for revived proxies
- Other values may appear if custom pipelines set `process`.

`issue_tag`
- Compact security issue list derived from `proxy.security_issues`.
- Format: `SEC:<ISSUE1>,<ISSUE2>`.
- Empty when no issues are present.
- Tokens are normalized (see "Security Issue Tags").

### Cleanup Rules

After formatting, the output is normalized as follows:

- Empty bracket pairs (`[]`, `()`, `{}`) are removed.
- Duplicate separators (`-`, `_`, `|`, spaces, tabs) are collapsed.
- Leading/trailing separators are trimmed.
- Remaining whitespace is normalized to single spaces.

## Structured Tags

Structured tags live in `proxy.tags` as a list of strings. If a proxy already
has tags, new tags are appended without duplication.

### Core Tags

- `PROTO:<PROTO>`
  - Uppercased protocol name (e.g., `VLESS`, `VMESS`, `TROJAN`, `SSH`, `SOCKS5`).
- `TRANS:<TRANSPORT>`
  - One of `WS`, `GRPC`, `H2`, `TCP`, `KCP`, `QUIC`, `UDP` (see transport mapping).
- `SEC:<SECURITY>`
  - `TLS` or `REALITY` when detected; omitted otherwise.
- `PROC:<PROCESS>`
  - Uppercased `process` (`NATIVE`, `REVIVED-WARP`, `REVIVED-VWARP`, etc.).
- `STATUS:UP` / `STATUS:DOWN`
  - Derived from `proxy.is_working`.
- `GEO:<FLAG>`
  - Country flag emoji from `country_code`, or `🌐` if unknown.
- `LAT:<N>MS`
  - Integer latency in milliseconds when known.

### Revival Tags

- `REVIVED`
  - Added when the washer successfully revives a failed proxy.
- `WARP` / `VWARP`
  - Indicates the chain type used for revival.

### Security Issue Tags

Security issues are always included when present in `proxy.security_issues`.
The values are normalized into tokens and emitted as:

- `ISSUE:<CATEGORY>:<REASON>`
- `ISSUE:<CATEGORY>` (when reason is empty)
- `ISSUE:<REASON>` (when category is absent)

Normalization rules:

- Tokens keep alphanumerics plus `_.-+`.
- Everything else is stripped.
- Tokens are uppercased for categories and preserved for reasons.

### Tag Ordering

Tags are added in this order:

1. `PROTO:*`
2. `TRANS:*`
3. `SEC:*`
4. `PROC:*`
5. `REVIVED`, then `WARP` or `VWARP` (if applicable)
6. `STATUS:*`
7. `GEO:*`
8. `LAT:*`
9. `ISSUE:*` entries
10. Any existing tags on the proxy (deduplicated)

## Examples

### Example Name

`🇺🇸 | VLESS+WS+TLS | 120ms | UP | NATIVE | SEC:MALWARE:DNS_LEAK`

### Example Tag List

- `PROTO:VLESS`
- `TRANS:WS`
- `SEC:TLS`
- `PROC:NATIVE`
- `STATUS:UP`
- `GEO:🇺🇸`
- `LAT:120MS`
- `ISSUE:MALWARE:DNS_LEAK`

## Notes

- Duplicate name suffixes (for example `#2`) are not added; duplicates are
  removed earlier in the pipeline.
- Use the template if you want to add or remove sections without changing the
  structured tag list.

