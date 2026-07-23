# Ed25519 Manifest Signing & Web Crypto Audit Report

## Ed25519 Manifest Signing & Web Crypto Flowchart

```ascii
+------------------------+                     +---------------------------+
|    ConfigStream CI     |                     |     Browser (Client)      |
|  (Artifact Generation) |                     |    (Web Crypto API)       |
+------------------------+                     +---------------------------+
| 1. Generate Manifest   |                     | 1. Fetch JSON Artifact    |
|    (JSON object)       |                     |                           |
|                        |                     | 2. Canonicalize JSON      |
| 2. Canonicalize JSON   |                     |    (Sort keys α-betically)|
|    (sort_keys=True)    |                     |                           |
|                        |                     | 3. Read Timestamp         |
| 3. Prepend Timestamp   |======(Network)=====>|    (Uint64, Big-Endian)   |
|    (Uint64 Big-Endian) |                     |                           |
|                        |                     | 4. Validate Freshness     |
| 4. Sign Payload        |                     |    (Max 300s, Skew 30s)   |
|    (Ed25519 Priv Key)  |                     |                           |
|                        |                     | 5. Verify Ed25519 Sig     |
| 5. Inject Signature    |                     |    (window.crypto.subtle) |
+------------------------+                     +---------------------------+
```

## Canonical JSON Sorting & Signature Verification Table

| Component | File | Mechanism / Assessment |
|-----------|------|------------------------|
| **Key Generation / Extraction** | `signer.py` | Handles 64-byte hex (seed + pub) by correctly slicing the first 32 bytes (`key_bytes[:32]`) to extract the Ed25519 seed. |
| **Python Canonicalization** | `validate_pages_artifact.py` | Pops `manifest_signature` and dumps JSON with `sort_keys=True`, `separators=(",", ":")`, and `ensure_ascii=False`. Reliable serialization. |
| **JS Canonicalization** | `verifier.js` | Uses recursive `_canonicalize` to sort object keys alphabetically and strings them via `JSON.stringify`. Matches Python's byte output. |
| **JS Key Injection** | `verifier.js` | Rejects placeholder keys (`PLACEHOLDER`, `79e/79e/`). Validates length `>= 60` (handles Base64 SPKI). Imports via `crypto.subtle.importKey`. |
| **Web Crypto Verification** | `verifier.js` | Decodes Base64 to ArrayBuffer. Verifies Ed25519 signature correctly natively using Web Crypto API. Fail-closed error handling. |

## Timestamp Window & Replay Protection Assessment

The replay protection mechanism is robustly implemented across Python and JavaScript:

1. **Embedding**: The timestamp is prepended to the canonical content bytes as an 8-byte big-endian unsigned integer (`struct.pack(">Q")` in Python, manual bit-shifting in `verifier.js`). This tightly binds the cryptographic signature to the issuance time.
2. **Window Validation**:
   - Both `signer.py` and `verifier.js` enforce `SIGNATURE_MAX_AGE_SECONDS = 300` (5 minutes). Signatures older than this are rejected regardless of cryptographic validity.
   - NTP drift is accommodated using `CLOCK_SKEW_TOLERANCE_SECONDS = 30`. Timestamps up to 30 seconds into the future are accepted, mitigating false-positives from clock desynchronization.

## Key Storage & Environment Variable Protection Audit

1. **Python (`validate_pages_artifact.py`)**: 
   - Looks up `CS_SIGNING_PRIVATE_KEY_HEX` and `CONFIGSTREAM_SIGNING_PRIVATE_KEY_HEX`.
   - Prevents telemetry and logs from exposing keys by scanning files (`pipeline_events.jsonl` and ZIP assets) against regex `ZIP_DEPLOY_SECRET_RE`.
2. **JavaScript (`stego.js` / `verifier.js`)**:
   - In `stego.js`, Fernet keys (`STEGO_KEY`) are checked to ensure they aren't placeholders (`_isPlaceholderSecretKey`).
   - In `verifier.js`, the `PUBLIC_KEY` is loaded from `CS_CONSTANTS.PUBLIC_KEY`. The `_isConfiguredPublicKey` check securely drops CI placeholders.

## Hardening & Key Rotation Roadmap

1. **Implement Key Versioning**: Current implementation uses a single static public key. Introduce a `key_id` in the signature object to allow multi-key rotation and revocation without breaking client updates.
2. **Content Security Policy (CSP)**: Ensure CSP headers strictly restrict inline scripts to prevent XSS-based exfiltration of `CS_CONSTANTS`. Web Crypto API limits extraction if keys are marked non-extractable, but since the client only has the public key, the primary risk is XSS bypassing the verification entirely.
3. **Restrict JS Global Scope**: `window.CS_CONSTANTS` and `global.Verifier` are exposed to the global scope. Moving verification inside an IIFE closure or ES6 module and removing global references will harden the client against tampering.
4. **Steganography Fail-Over**: `stego.js` falls back to `fernetBrowser` if LSB extraction fails. Ensure legacy path deprecation to minimize attack surface on old cryptographic libraries.
