# Client Format Artifact Contracts

ConfigStream validates generated client artifacts at the Pages release boundary.

- Sing-box configs validate outbound and endpoint tags, selector and URL-test members, detours, routing targets, and DNS detours.
- Mihomo configs reject deprecated relay groups and validate `dialer-proxy`, proxy-group, and routing-policy references.
- Xray output uses modern flat VMess and VLESS settings and validates outbound tags, proxy chaining, and routing references.
- NekoBox-compatible plaintext and Base64 subscriptions are checked for UTF-8 share-link syntax and exact decode parity.

The authoritative machine-readable inventory remains `docs/output_matrix.json`; implementation status remains `docs/core_compatibility_report.json`.
