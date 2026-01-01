# Phase 11: Transport & Vectors (Deep Internals) - Analysis Report

## 11. Overview
This phase analyzes deep internal mechanisms: Steganography transport (hiding configs in images) and Vector generation (for client-side similarity features).

## 11.1. Steganography Transport (`src/configstream/transport/stego.py`)

### 11.1.1. Mechanism
**Analysis**:
*   **Technique**: Append-only Steganography.
    *   `final_bytes = image_bytes + MAGIC_MARKER + encrypted_payload`.
    *   This is "dumb" steganography. It doesn't modify pixels (LSB).
    *   **Pros**: Extremely fast, robust against some format checks (PNG usually ignores trailing data).
    *   **Cons**: Detectable by file size analysis or simple hex inspection. CDN image optimization might strip it.
*   **Encryption**:
    *   Uses `Fernet` (AES-128-CBC + HMAC).
    *   Key management: `CONFIG_STREAM_KEY` env var.
*   **Magic Marker**: `b"CSTREAM_PAYLOAD_START>>"`.
*   **Safety**:
    *   `zlib.compress` before encryption reduces size.
    *   HMAC prevents tampering (part of Fernet).

### 11.1.2. Usage
*   `generate_stego_assets` function iterates over `*.png` in assets folder and creates `stealth_*.png`.
*   **Integration**: It is NOT called by the main pipeline (`src/configstream/pipeline.py` or `output_handler.py`). It is imported by `scripts/merge/generators.py`.
    *   **Implication**: Steganography is an optional post-processing step triggered by separate scripts, not the core pipeline. This separates concerns but means a standard `configstream` run won't produce stego assets unless configured to run the script.
*   Frontend needs the matching KEY to decrypt.

## 11.2. Vector Intelligence (`src/configstream/intelligence/vectors.py`)

### 11.2.1. Feature Hashing
**Analysis**:
*   **Goal**: Generate lightweight features for client-side sorting/filtering (e.g. "Find similar proxies").
*   **Dimensions (0-7)**:
    0.  Protocol (hash%10)
    1.  Country (hash%10)
    2.  Latency (0, 1, 2)
    3.  Port (mod 10)
    4.  ISP (hash%10)
    5.  Security (Heuristic 0-9)
    6.  Stability (Fixed 5)
    7.  Reliability (Fixed 5)
*   **Utility**: This allows a JS frontend to compute cosine similarity or Euclidean distance between proxies without needing a backend query.
*   **Determinism**: SHA-256 ensures consistent hashing across runs.
*   **Implementation**: `AtomicFileWriter.write_text` handles output safely.
*   **Optimization**: Hash calculations use `sha256(....hexdigest())` which creates an intermediate string. `sha256(b"...")` and accessing bytes directly or `int.from_bytes` would be slightly faster, but negligible for this scale.

## Recommendations
1.  **Stego Integration**: Consider adding a hook in `output_handler.py` to optionally trigger `generate_stego_assets` if a flag is set, ensuring it's part of the main build loop.
2.  **Stego Robustness**: Verify if Cloudflare Pages or GitHub Pages gzip compression strips the trailing bytes. Usually they compress the *transfer*, not the file, so it should be safe. However, image optimization plugins *will* strip it.
3.  **Vector Expansion**: Pass `ProxyHistoryTracker` to `generate_vectors` to populate the currently placeholder "Stability" and "Reliability" dimensions (indices 6 and 7).
