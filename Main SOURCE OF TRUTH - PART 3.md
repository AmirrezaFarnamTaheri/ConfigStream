
#### Response:
#### Side quest: Xray / Sing-box JSON format vs ConfigStream generated JSON

##### Scope

I checked the **official config shapes** for Sing-box and Xray, then compared them against ConfigStream’s current generator/validator contracts. I still do **not** have the actual latest generated `output/` folder, so this is a **source-contract check**, not a byte-for-byte validation of the latest artifacts.

### 1. Official Sing-box JSON shape

Sing-box uses JSON config files. The current official top-level structure includes keys such as:

```json
{
  "log": {},
  "dns": {},
  "ntp": {},
  "certificate": {},
  "certificate_providers": [],
  "http_clients": [],
  "endpoints": [],
  "inbounds": [],
  "outbounds": [],
  "route": {},
  "services": [],
  "experimental": {}
}
```

The official docs also expose `sing-box check`, `sing-box format`, and `sing-box merge` for config validation/formatting/merging. ([sing-box.sagernet.org](https://sing-box.sagernet.org/configuration/?utm_source=chatgpt.com))

Important: Sing-box uses **`route`**, not Xray’s `routing`. Sing-box `outbounds` are objects with at least `type` and `tag`, and supported outbound types include `direct`, `block`, `socks`, `http`, `shadowsocks`, `vmess`, `trojan`, `wireguard`, `hysteria`, `vless`, `shadowtls`, `tuic`, `hysteria2`, `anytls`, `tor`, `ssh`, `dns`, `selector`, `urltest`, and `naive`. ([sing-box.sagernet.org](https://sing-box.sagernet.org/zh/configuration/outbound/?utm_source=chatgpt.com))

### 2. Official Xray JSON shape

Xray’s official configuration is also JSON, but its top-level structure is different:

```json
{
  "version": {},
  "log": {},
  "api": {},
  "dns": {},
  "routing": {},
  "policy": {},
  "inbounds": [],
  "outbounds": [],
  "transport": {},
  "stats": {},
  "fakedns": {},
  "metrics": {},
  "observatory": {},
  "burstObservatory": {},
  "geodata": {}
}
```

Xray uses **`routing`**, not `route`. Its `outbounds` use fields such as `protocol`, `settings`, `tag`, `streamSettings`, `proxySettings`, `mux`, and `targetStrategy`; the first outbound is the primary/default outbound when routing has no match. ([Project X](https://xtls.github.io/en/config/?utm_source=chatgpt.com)) ([Project X](https://xtls.github.io/en/config/outbound.html?utm_source=chatgpt.com))

So a Sing-box config and an Xray config are not interchangeable even though both are JSON.

### 3. ConfigStream’s current public JSON output families

From the output matrix, ConfigStream currently defines these major JSON output classes:

1. **Sing-box runnable/config-like outputs**
   - `singbox.json`
   - `singbox-dns-safe.json`
   - `singbox-dns-hardened.json`
   - `singbox-vpn.json`
   - `singbox-vpn-dns-safe.json`
   - `singbox-vpn-dns-hardened.json`
   - `singbox-chains.json`
   - `singbox-chains-dns-safe.json`
   - `singbox-chains-dns-hardened.json`

2. **Chain metadata outputs**
   - `chains.json`
   - `chains-dns-safe.json`
   - `chains-dns-hardened.json`

3. **Canonical data/control JSON**
   - `proxies.json`
   - `metadata.json`
   - `artifact_manifest.json`
   - `health.json`
   - `api/proxies`
   - `api/stats`
   - analytics JSON under `data/`

The matrix says Sing-box and Clash references are semantically validated, while `proxies.json` is the canonical public proxy JSON list, not a Sing-box or Xray config. `output_matrix.json`

### 4. ConfigStream’s Sing-box generator: mostly aligned, but has cleanup issues

`src/configstream/generators/singbox.py` generates a Sing-box config with:

- `log`
- `dns`
- `inbounds`
- `outbounds`
- `route`
- `experimental`

That matches the broad Sing-box config model. The generator creates selector and urltest groups, proxy outbounds, `direct`, `block`, and `dns-out`, plus DNS and route rules. `singbox.py`

The converter maps ConfigStream `Proxy` objects into Sing-box outbound objects and handles many protocol-specific cases: VMess, VLESS, Shadowsocks, Trojan, HTTP, SSH, Hysteria, SOCKS, Naive, WireGuard, Hysteria2, TUIC, and revived chain outbounds. It also explicitly drops unsupported or unsafe conversions in many cases, including missing UUID/password/private keys, local/private endpoints, unsupported Shadowsocks plugins, unsupported AnyTLS, and several protocols that are parsed but not exported to Sing-box. `singbox.py`

#### Important issue: dead appended outbounds

In `generators/singbox.py`, the code builds:

```python
final_outbounds = [
    selector_outbound,
    urltest_outbound,
    *outbounds,
    {"type": "direct", "tag": "direct"},
    {"type": "block", "tag": "block"},
    {"type": "dns", "tag": "dns-out"},
]
```

After that, it appends extra selector/urltest/mode-selector objects to `outbounds`, but `final_outbounds` has already expanded `*outbounds`. Those later appended objects do **not** make it into the returned config. `singbox.py`

That looks like stale/dead generation logic. It may not break the output, but it creates misleading code and should be cleaned or moved before `final_outbounds` is assembled.

### 5. ConfigStream’s Pages validator is strong, but not enough for complete native-core proof

`validate_pages_artifact.py` requires the public JSON/YAML/ZIP/control files, checks required non-empty files, validates JSON parseability, validates ZIP integrity and safe paths, verifies manifest size/hash coverage, checks API alias parity, and performs semantic reference checks for Sing-box and Clash. It can optionally run native client checks using local `sing-box` and `mihomo`/Clash binaries. `validate_pages_artifact.py`

That is good, but the important limitation is:

**Native Sing-box validation is optional.**

So the current validator can prove “JSON parses and internal references look sane,” but unless `--native-client-check` runs in an environment with `sing-box`, it does not prove every generated Sing-box file is accepted by the actual Sing-box binary.

Recommended amendment:

- Add a dedicated CI job with pinned `sing-box` binary.
- Run `sing-box check -c` on:
  - `singbox.json`
  - `singbox-vpn.json`
  - all DNS-safe/hardened variants
  - full chain configs, if they are meant to be runnable
- If `singbox-chains.json` is only an outbound fragment, do **not** call it a full config; label it as a fragment and validate it with a wrapper config.

### 6. Xray JSON is not currently a first-class public pipeline output

The Lab docs claim the browser lab can export **Xray JSON** as one of the Step 5 formats. `Lab_Page.md`

However, `docs/output_matrix.json` does **not** list a public `xray.json`, `xray-dns-safe.json`, or `xray-chains.json` output. `output_matrix.json`

So the current state appears to be:

- **Sing-box JSON:** canonical pipeline output family.
- **Xray JSON:** lab export feature / frontend feature, not a canonical Pages output family.
- **`proxies.json`:** canonical dataset array, not Xray/Sing-box config.
- **`chains.json`:** chain metadata, not necessarily core-runnable config.

Add a formal Xray output track only when all of these exist:

- `docs/output_matrix.json` entries.
- Xray generator module.
- Xray semantic validator.
- Optional native `xray run -test` / `xray test` check, depending on available Xray command behavior.
- Lab and pipeline share one Xray builder.
- Xray docs explain unsupported protocols and transport differences.

### 7. Critical namespace differences to enforce

A validator should explicitly reject accidental cross-core mixing.

#### Sing-box config must use:

```json
{
  "inbounds": [],
  "outbounds": [
    {
      "type": "vless",
      "tag": "..."
    }
  ],
  "route": {}
}
```

#### Xray config must use:

```json
{
  "inbounds": [],
  "outbounds": [
    {
      "protocol": "vless",
      "settings": {},
      "streamSettings": {},
      "tag": "..."
    }
  ],
  "routing": {}
}
```

Main guardrails:

- Sing-box outbound key is `type`.
- Xray outbound key is `protocol`.
- Sing-box routing key is `route`.
- Xray routing key is `routing`.
- Sing-box TLS/transport fields are protocol-specific inside the outbound shape.
- Xray transport/security fields generally live under `streamSettings`.

This distinction should be turned into a test so a generated Xray file can never accidentally look like Sing-box JSON, and a Sing-box file can never accidentally look like Xray JSON.

### 8. Output naming risks

#### `singbox-chains.json`

The matrix describes this as “Sing-box chain outbounds.” `output_matrix.json`

If this file is intended to be imported as a full Sing-box config, it should contain a complete runnable config with at least usable `inbounds`, `outbounds`, and `route`.

If it is only intended as an outbound fragment, the name and docs should say:

- `singbox-chain-outbounds.json`
- or `singbox-chains.fragment.json`
- or “merge fragment; not runnable alone”

Recommended improvement:

Generate both:

1. `singbox-chains.json` - full runnable config.
2. `singbox-chain-outbounds.json` - fragment for advanced users.

#### `chains.json`

This should be treated as metadata, not core config.

#### `proxies.json`

This should continue to be a JSON array dataset, never a core config. README already says `proxies.json` is always a JSON array and metadata lives in `metadata.json`. `README.md`

### 9. Protocol export caveat

The Sing-box converter explicitly skips or drops some protocols in conversion. It logs unsupported conversion for protocols such as:

- `ssr`
- `snell`
- `brook`
- `juicity`
- `xray`
- `openvpn`
- `v2ray`

That means ConfigStream can parse or list these protocols, but they are **not all exportable to Sing-box** through the current converter. `singbox.py`

This is not necessarily a bug. It only becomes a bug if the UI/docs imply that every parsed protocol is exported into every core format.

Every output card should show:

- parsed: yes/no
- validated: yes/no
- Sing-box export: yes/no
- Xray export: yes/no
- Clash export: yes/no
- URI export: yes/no
- side-product export: yes/no

The existing protocol matrix already starts this separation and should be extended into a full import/export/client matrix. `protocol_matrix.json`

### 10. Remote rule-set issue in Sing-box JSON

ConfigStream’s Sing-box generator embeds remote rule-set URLs from GitHub for geosite/geoip assets. `singbox.py`

That is convenient, but in hostile networks it can fail at runtime if GitHub is blocked. For anti-censorship outputs, this is a practical weakness.

Recommended outputs:

1. `singbox.json` - current full version with remote rule sets.
2. `singbox-lite.json` - no remote rule-set dependency.
3. `singbox-offline.json` - embeds or bundles local rule-set assets where licensing allows.
4. `singbox-no-geosite.json` - minimal direct/proxy rules only.
5. `singbox-dns-hardened-lite.json` - hardened DNS without remote rule downloads.

Checklist:

- Every remote dependency documented.
- Offline variant available.
- UI labels “requires GitHub rule-set download.”
- Native check runs both online and no-network variants.

### 11. Required validators to add

#### Sing-box validator

For every Sing-box JSON:

- JSON parses.
- Top-level is object.
- Has `outbounds`.
- All outbound tags unique.
- Selector/urltest refs exist.
- `detour` refs exist.
- Route outbound refs exist.
- DNS detour refs exist.
- No internal `_` fields.
- No top-level Xray-only keys like `routing`.
- Optional native `sing-box check -c`.
- Version matrix check for current and previous Sing-box versions.

#### Xray validator

For every Xray JSON:

- JSON parses.
- Top-level is object.
- Has `outbounds`.
- Outbounds use `protocol`, not `type`.
- Outbounds with transport use `streamSettings`.
- Routing uses `routing`, not `route`.
- Route rule `outboundTag` values exist.
- No Sing-box-only `selector`/`urltest` outbounds unless translated appropriately.
- No Sing-box-only DNS outbound shape.
- Optional native Xray config test.
- Version matrix check for supported Xray core versions.

#### Dataset validator

For `proxies.json`:

- Root is array.
- Each proxy has required schema fields.
- Protocol is canonical or known alias.
- No raw secrets in metadata fields.
- Config URI is valid or marked unavailable.
- `is_working` is boolean.
- `process` / lifecycle is valid.
- `latency` is numeric/null.
- `details` does not contain deploy secrets.

### 12. Recommended new output plan

Add a formal split:

#### Core configs

- `singbox.json`
- `singbox-vpn.json`
- `singbox-lite.json`
- `singbox-offline.json`
- `xray.json`
- `xray-lite.json`
- `xray-reality.json`
- `xray-worker.json`

#### Fragments

- `singbox-outbounds.json`
- `singbox-chain-outbounds.json`
- `xray-outbounds.json`
- `xray-routing-fragments.json`

#### Data

- `proxies.json`
- `metadata.json`
- `chains.json`
- `revived.json`
- `health.json`
- `artifact_manifest.json`

#### Reports

- `core_compatibility_report.json`
- `singbox_check_report.json`
- `xray_check_report.json`
- `protocol_export_matrix.json`
- `output_validation_report.html`

### 13. Immediate action items

1. **Clean `generators/singbox.py` dead selector/urltest append logic.**
   Either include those additional outbounds in `final_outbounds` or delete them.

2. **Clarify `singbox-chains.json`.**
   Decide whether it is a full config or a fragment. Rename or generate both.

3. **Add Xray to output matrix only if pipeline actually generates it.**
   Lab-only Xray export should be tracked in a lab export matrix, not public output matrix.

4. **Add `core_format` metadata to JSON outputs.**

```json
{
  "core_format": "sing-box",
  "core_format_version": "1",
  "configstream_schema_version": "3.0.2"
}
```

For datasets:

```json
{
  "artifact_type": "dataset",
  "dataset_schema": "proxies-array"
}
```

5. **Add native-core validation job.**
   Pin `sing-box` and Xray binaries in CI, run validation on deterministic generated fixtures.

6. **Generate an explicit compatibility report.**
   Users should see which protocols survived into each output family.

7. **Create offline/lite Sing-box variants without remote rule-set dependencies.**

### Bottom line

ConfigStream’s **Sing-box JSON direction is structurally aligned** with the official Sing-box config model, and the Pages validator already catches many reference/shape errors. But it still needs cleanup and stronger proof through pinned native `sing-box check`.

ConfigStream’s **Xray JSON is not yet a first-class pipeline output**. It is documented as a Lab export, but not represented in the canonical output matrix. To make Xray real and trustworthy, it needs a dedicated generator, validator, output matrix entries, native Xray checks, and a clear distinction from Sing-box JSON.

The most important rule: **never mix the two JSON dialects.** Sing-box JSON and Xray JSON are both JSON, but they are different config languages.

**Sources:**

- [Introduction - sing-box](https://sing-box.sagernet.org/configuration/?utm_source=chatgpt.com)
- [Configuration File | Project X](https://xtls.github.io/en/config/?utm_source=chatgpt.com)
