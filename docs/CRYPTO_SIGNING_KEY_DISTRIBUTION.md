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
- **Final release verification**: the final artifact contract receives `CS_PUBLIC_KEY`, so a signed release is cryptographically checked against the configured distribution trust anchor rather than only validating signature shape or file hashes.
- **Frontend allowlist**: runtime-config generation deliberately ignores unrelated secrets that may exist in the CI environment. Only the public Ed25519 verification key and public IPNS routing key are selected for browser publication.
- **Archive scanning**: Pages-artifact validation scans deployable archives for forbidden secret markers and other credential-like material.
- **Telemetry scrubbing**: pipeline-event validation checks for credential markers such as bearer/authorization material and known placeholder secret strings.

### 4.1 Production GitHub Actions bootstrap

The production release path supports both unsigned and signed publication. The `Validate main release prerequisites` step runs for non-pull-request executions on `refs/heads/main` before release fan-out and validates any configured signing material.

1. **Unsigned mode**: when neither `CS_SIGNING_PRIVATE_KEY_HEX` nor `CS_PUBLIC_KEY` is configured, release preflight may proceed in explicit unsigned mode. Artifact hashes, source-coverage gates, native-client checks, release gating, and publication controls still apply.
2. **Signed mode**: provision `CS_SIGNING_PRIVATE_KEY_HEX` through the authorized GitHub Actions secret path. Never echo or serialize the private key into artifacts or logs.
3. **Optional explicit public key**: `CS_PUBLIC_KEY` may accompany the private key. If omitted, the browser verification key is derived from the private key. If supplied, preflight and promotion require it to match the signing key.
4. **No public-key-only signed configuration**: a public key without signing material is rejected because the release could advertise a trust anchor while being unable to produce matching signatures.
5. **Legacy alias migration**: direct/external callers may still use `CONFIGSTREAM_SIGNING_PRIVATE_KEY_HEX`; GitHub Actions should use `CS_SIGNING_PRIVATE_KEY_HEX`.
6. **Public runtime config is not a secret store**: do not add `STEGO_KEY`, `CONFIG_STREAM_KEY`, API tokens, signing keys, or any other confidential value to `runtime-config.js`.

## 5. Remaining hardening considerations

1. **Key rotation**: manifest signatures already carry a `key_id`, but browser distribution still exposes one active trust anchor. A future rotation design can publish an explicitly bounded set of accepted public keys and deprecation metadata for zero-downtime rollover.
2. **Trust-anchor delivery**: because `runtime-config.js` supplies the browser trust anchor, deployment integrity still matters. Keep CSP and artifact-integrity controls aligned so an attacker who can rewrite the static site cannot silently replace both content and its verification key.
3. **64-byte private-key validation**: accepting the first 32 bytes of a supported 64-byte Ed25519 representation is compatible with the Python library, but callers should prefer the canonical 32-byte seed or add explicit validation of the appended public half when importing full keypair encodings.
4. **Private stego deployments**: if a private deployment needs browser-side stego decryption, distribute the symmetric key through an authenticated, non-public channel. Do not weaken the public runtime-config validator to make static delivery convenient.
