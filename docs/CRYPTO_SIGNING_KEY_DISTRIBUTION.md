# Cryptographic Signing & Public Key Distribution Audit

This document reviews the Ed25519 cryptographic signing pipeline, frontend verification logic, and secret handling mechanisms across ConfigStream.

## 1. Cryptographic Signing & Verification Trust Chain

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
| [constants.js]                 [verifier.js / WebCrypto]                          |
|        |                                   |                                      |
|        +---------------------------------->+---(Verify Timestamp & Signature)---> |
|                                                                    [Valid Data]   |
+-----------------------------------------------------------------------------------+
```

## 2. Ed25519 Key Generation & Canonical JSON Spec Verification

| Component | Specification | Implementation Detail |
| :--- | :--- | :--- |
| **Key Algorithm** | Ed25519 | Utilizes `cryptography.hazmat.primitives.asymmetric.ed25519` in Python. |
| **Private Key Format** | 32-byte seed or 64-byte key | `signer.py` accepts hex-encoded keys. If 64 bytes are provided, it truncates to the first 32 bytes (seed value). |
| **Public Key Format** | SPKI/Base64 or Raw Hex | Hex via `signer.get_public_key_hex()`; frontend accepts Base64/SPKI format (~68 chars). |
| **Canonical JSON** | `artifact_manifest.json` | Strips `manifest_signature`, sorts keys `sort_keys=True`, removes ASCII escaping, encodes as UTF-8 bytes. |
| **Payload Structure**| Signed Subscriptions | Embeds big-endian uint64 timestamp. Payload layout: `timestamp (8 bytes) || content_bytes`. |
| **Replay Protection**| Age & Skew Validation | Signatures older than `300` seconds are rejected. Accepts up to `30` seconds of future skew (NTP drift). |

## 3. Frontend Signature Verification & Key Injection Security Audit

- **Key Injection**: The CI pipeline writes environment variables (like `PUBLIC_KEY` and `STEGO_KEY`) into `frontend/assets/js/runtime-config.js` via string replacement or template generation.
- **Verification Logic**: `verifier.js` uses the native Web Crypto API (`window.crypto.subtle`). It builds the identical signed payload `[timestamp] || [content]` and verifies it against the `PUBLIC_KEY`.
- **Fail-Closed Design**: If the `PUBLIC_KEY` is missing, contains placeholder values (e.g., `PLACEHOLDER`, `79e/79e/`), or is less than 60 characters, verification fails and no data is trusted.
- **Steganography Security**: `stego.js` uses a symmetric Fernet token (HMAC + AES-CBC). It explicitly checks for and rejects placeholder keys (`PLACEHOLDER_KEY_INJECTED_BY_CI`). The key must be at least 40 characters (standard Fernet is 44 URL-safe Base64 chars).
- **Time Validation**: The frontend strictly validates the embedded timestamp against the client's current time, throwing a `SECURITY ALERT` if the timestamp exceeds the `300s` maximum age or the `-30s` skew tolerance.

## 4. Secret Handling & Environment Variable Protection Assessment

- **Manifest Private Key**: Sourced from `CS_SIGNING_PRIVATE_KEY_HEX` or `CONFIGSTREAM_SIGNING_PRIVATE_KEY_HEX`. Handled strictly in memory during the build phase (`_manifest_signer_from_env()`).
- **Archive Scanning**: `validate_pages_artifact.py` includes a `ZIP_DEPLOY_SECRET_RE` regex scan to ensure high-entropy strings, `CS_PUBLIC_KEY`, `ADMIN_API_KEY`, etc., do not accidentally leak into generated ZIP archives like `side_products.zip`.
- **Telemetry Scrubbing**: Event logs (`pipeline_events.jsonl`) are checked for forbidden markers (e.g., `Bearer`, `Authorization:`, and placeholder key strings) to prevent secret leakage via monitoring infrastructure.
- **Public Key Parser**: The Python validation script tries decoding `CS_PUBLIC_KEY` first as Base64/DER, then falls back to Raw Hex, demonstrating resilience in CI checks.

## 5. Hardening Recommendations

1. **Strict Key Formatting**: `_public_key_from_runtime_env` falls back quietly through various parsing formats (Base64 -> DER -> Hex). It is safer to strictly enforce a single representation (e.g., standard Base64 SPKI) to prevent ambiguity attacks.
2. **Key Rotation Mechanism**: There is currently no built-in key rotation versioning. Adding a `key_id` to signatures and a `keys` array in `runtime-config.js` would allow zero-downtime rotation.
3. **CSP Enforcement for runtime-config.js**: Because `runtime-config.js` dictates trust anchors, ensure the final generated HTML enforces strict Content Security Policies (CSP) to prevent modification of `window.CS_RUNTIME_CONFIG` by XSS attacks.
4. **Fernet Key Distribution**: The `STEGO_KEY` is symmetric. Since it's distributed inside `runtime-config.js`, any user loading the client can extract it and decode the stego payloads. If confidentiality of stego endpoints is required against sophisticated adversaries, an asymmetric encryption model (or authenticated backend exchange) should replace Fernet.
5. **Private Key Truncation Safety**: While taking the first 32 bytes of a 64-byte Ed25519 key (seed) is standard for Python's cryptography library, it relies on the user providing a valid RFC 8032 format key. Validate that the derived public key matches the second half of the 64-byte string if a full keypair is supplied.
