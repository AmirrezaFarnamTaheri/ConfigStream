# Cryptographic Signing & Public Key Distribution Audit

This document describes the current Ed25519 signing pipeline, frontend verification trust anchor, and public-artifact secret-handling rules used by ConfigStream.

## 1. Cryptographic signing and verification trust chain

```text
+-----------------------------------------------------------------------------------+
|                                CI / Build Environment                             |
|                                                                                   |
|  [CS_SIGNING_PRIVATE_KEY_HEX] -----> [Signer (signer.py)]                         |
|                                            |                                      |
|                                            v                                      |
|                                     Sign Data / Manifest                          |
|                                            |                                      |
|  [CS_PUBLIC_KEY]                           v                                      |
|        |                       [artifact_manifest.json]                           |
|        v                       [Subscription Payloads]                            |
| [runtime-config.js]                                                               |
+--------|-----------------------------------|--------------------------------------+
         |                                   |
         v                                   v
+-----------------------------------------------------------------------------------+
|                                  Client Browser                                   |
|                                                                                   |
| [window.CS_RUNTIME_CONFIG]        [Network Fetch]                                 |
|        |                                   |                                      |
|        v                                   v                                      |
| [PUBLIC_KEY only as trust]     [verifier.js / WebCrypto]                          |
|        |                                   |                                      |
|        +---------------------------------->+---(Verify Signature)---------------> |
|                                                                    [Valid Data]   |
+-----------------------------------------------------------------------------------+
```

`runtime-config.js` is a public file. Artifact preparation therefore allowlists only browser-safe public material: the Ed25519 `PUBLIC_KEY` and the public `IPNS_KEY`. Symmetric encryption keys and signing private keys are forbidden from the generated runtime config.

## 2. Ed25519 key generation and canonical payloads

| Component | Specification | Implementation detail |
| :--- | :--- | :--- |
| **Key algorithm** | Ed25519 | Uses `cryptography.hazmat.primitives.asymmetric.ed25519`. |
| **Private-key input** | 32-byte seed or supported 64-byte form | `Signer` accepts hex-encoded key material and uses the 32-byte seed required by `cryptography`. |
| **Public-key input** | SPKI/Base64, raw Base64, or raw hex | Python normalizes supported encodings to the 32-byte raw key; browser runtime config emits SPKI/Base64. |
| **Manifest canonicalization** | `artifact_manifest.json` | Removes `manifest_signature`, sorts keys, uses compact JSON separators, preserves UTF-8, and signs the timestamp-prefixed canonical bytes. |
| **Subscription payload** | Signed content | Signs `timestamp (8-byte big-endian uint64) || content_bytes`. |
| **Subscription replay window** | 300 seconds by default | Subscription verification rejects signatures older than the configured maximum and allows up to 30 seconds of future clock skew. |
| **Manifest lifetime** | Static release record | Manifest verification validates the signed timestamp and rejects implausibly future timestamps, but does not apply the short subscription TTL unless a caller explicitly supplies `max_age_seconds`. |
| **Manifest key binding** | `key_id` | `manifest_signature.key_id` is derived from SHA-256 of the public key and is checked during verification. |

## 3. Frontend signature verification and public runtime config

- **Runtime-config generation**: `scripts/validate_frontend_placeholders.py --inject-env` writes only allowlisted public values. It may use `CS_PUBLIC_KEY` directly or derive the public key from `CS_SIGNING_PRIVATE_KEY_HEX`, but it never publishes the private key.
- **Symmetric-key exclusion**: strict validation rejects any `STEGO_KEY` or `CONFIG_STREAM_KEY` field in `assets/js/runtime-config.js`. The public release path must not ship a symmetric steganography/decryption key to browsers.
- **Verification logic**: `verifier.js` uses Web Crypto and the public Ed25519 trust anchor from `window.CS_RUNTIME_CONFIG` to verify signed content using the same timestamp-prefixed payload format as Python.
- **Fail-closed signed objects**: when a signature is present, a missing/malformed public key, placeholder trust material, key-ID mismatch, or invalid signature must fail verification instead of silently treating the object as trusted.
- **Steganography**: Fernet/LSB stego processing may still use a symmetric key during private generation or explicitly private consumption. Public artifact preparation does not distribute that key. Consequently, public static clients must not depend on embedded symmetric-key delivery for confidentiality or decryption.

## 4. Secret handling and environment-variable protection

- **Manifest private key**: runtime signing helpers accept `CS_SIGNING_PRIVATE_KEY_HEX` and retain `CONFIGSTREAM_SIGNING_PRIVATE_KEY_HEX` as a legacy direct-invocation alias. The production workflow exposes the canonical secret name only.
- **Public/private binding**: release preflight rejects malformed key material and rejects a configured `CS_PUBLIC_KEY` that does not match the signing private key. Promotion re-signs the final manifest, verifies the produced signature immediately, and—when `CS_PUBLIC_KEY` is configured—verifies the signature against that configured distribution key before publication can continue.
- **Pages trust boundary**: artifact generation and Pages deployment are intentionally separate trust decisions. Signed Pages publication requires an independently configured matching `CS_PUBLIC_KEY` secret. The deployment workflow checks the candidate, last-known-good snapshot, deployed candidate, and restored rollback against the same policy.
- **Explicit unsigned policy**: `config/pages-trust-policy.json` may opt one exact repository into genuinely unsigned Pages artifacts, and its repository binding prevents inherited fork activation. Repository Variable `ALLOW_UNSIGNED_PAGES=true|false` overrides the committed default. The same resolved policy is required for candidate verification, rollback snapshots, deployed smoke, and rollback smoke. It never authorizes a signed artifact whose public trust anchor is missing or invalid.
- **Final release verification**: the final artifact contract receives `CS_PUBLIC_KEY` when configured, so signed releases are cryptographically checked against the configured distribution trust anchor rather than only validating signature shape or file hashes.
- **Frontend allowlist**: runtime-config generation deliberately ignores unrelated secrets that may exist in the CI environment. Only the public Ed25519 verification key and public IPNS routing key are selected for browser publication.
- **Archive scanning**: Pages-artifact validation scans deployable archives for forbidden secret markers and other credential-like material.
- **Telemetry scrubbing**: pipeline-event validation checks for credential markers such as bearer/authorization material and known placeholder secret strings.

### 4.1 Production GitHub Actions bootstrap

The canonical generation path supports unsigned and signed artifacts, but Pages publication is secure-by-default and requires an explicit trust decision.

1. **Signed mode (recommended)**: provision `CS_SIGNING_PRIVATE_KEY_HEX` and the exact matching `CS_PUBLIC_KEY` as GitHub Actions repository secrets. The private key is used for signing; the public key independently authenticates what the Pages workflow receives and what it later observes over the network.
2. **Unsigned generation**: when neither signing value is configured, release preflight may generate an unsigned canonical artifact. Artifact hashes, source-coverage gates, native-client checks, release gating, and publication controls still apply.
3. **Unsigned Pages publication is explicit**: the canonical upstream uses the repository-bound `config/pages-trust-policy.json`; forks ignore that opt-in unless the bound repository matches. Operators may set repository Variable `ALLOW_UNSIGNED_PAGES=true` to enable or `false` to disable unsigned publication explicitly.
4. **No signed-to-unsigned downgrade**: if `artifact_manifest.json` contains `manifest_signature`, Pages requires a valid `CS_PUBLIC_KEY`. `ALLOW_UNSIGNED_PAGES=true` cannot convert a signed artifact into an unsigned trust decision.
5. **No public-key-only signing configuration**: main release preflight rejects `CS_PUBLIC_KEY` without signing material because the canonical release would advertise a trust anchor while being unable to produce matching signatures.
6. **Derived browser key vs deployment trust anchor**: artifact generation can derive the browser verification key from `CS_SIGNING_PRIVATE_KEY_HEX`, but Pages deliberately uses the separately configured `CS_PUBLIC_KEY` secret as an independent trust anchor. For signed Pages operation, configure both values.
7. **Legacy alias migration**: direct/external callers may still use `CONFIGSTREAM_SIGNING_PRIVATE_KEY_HEX`; GitHub Actions should use `CS_SIGNING_PRIVATE_KEY_HEX`.
8. **Public runtime config is not a secret store**: do not add `STEGO_KEY`, `CONFIG_STREAM_KEY`, API tokens, signing keys, or any other confidential value to `runtime-config.js`.

### 4.2 Pages verification boundaries

The Pages workflow applies the same policy at four points so one stage cannot silently weaken another:

1. **Candidate before upload**: validate the sealed manifest before any Pages artifact is uploaded.
2. **Last-known-good snapshot**: validate the currently deployed snapshot before accepting it as rollback material. Signed snapshots require `CS_PUBLIC_KEY`; genuinely unsigned snapshots require the same explicit `ALLOW_UNSIGNED_PAGES=true` policy as publication.
3. **Candidate after deployment**: verify the deployed release identity/integrity and pass `CS_PUBLIC_KEY` to remote verification when signed mode is active.
4. **Rollback after restoration**: re-check the last-known-good policy and verify the restored site with the same public trust anchor when signed mode is active.

This means a missing key, invalid key, invalid signature, or implicit unsigned fallback cannot be hidden by a later deployment or rollback step.

## 5. Remaining hardening considerations

1. **Key rotation**: manifest signatures already carry a `key_id`, but browser distribution still exposes one active trust anchor. A future rotation design can publish an explicitly bounded set of accepted public keys and deprecation metadata for zero-downtime rollover.
2. **Trust-anchor delivery**: because `runtime-config.js` supplies the browser trust anchor, deployment integrity still matters. Keep CSP and artifact-integrity controls aligned so an attacker who can rewrite the static site cannot silently replace both content and its verification key.
3. **64-byte private-key validation**: accepting the first 32 bytes of a supported 64-byte Ed25519 representation is compatible with the Python library, but callers should prefer the canonical 32-byte seed or add explicit validation of the appended public half when importing full keypair encodings.
4. **Private stego deployments**: if a private deployment needs browser-side stego decryption, distribute the symmetric key through an authenticated, non-public channel. Do not weaken the public runtime-config validator to make static delivery convenient.
