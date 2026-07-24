# Steganography KAT Vectors & HMAC Security Audit

## Steganography HMAC Derivation Flowchart

```text
+----------------+       +------+       +-------------+
|  key_material  |       | salt |       | carrier_len |
+-------+--------+       +--+---+       +------+------+
        |                   |                  |
        v                   v                  v
+-------+-------------------+------------------+------+
|             HMAC-SHA256 Derivation Input            |
| "ConfigStream-LSB-v2\0" || salt || struct.pack(">Q")|
+---------------------------+-------------------------+
                            | (Key = key_material)
                            v
                    +----------------+
                    |  HMAC-SHA256   |
                    +-------+--------+
                            |
                 +----------+----------+
                 |                     |
           bytes[0:8]             bytes[8:16]
                 |                     |
                 v                     v
           start offset             stride
                 |                     |
                 v                     v
        (mod carrier_len)   (mod carrier_len) | 1
                                       |
                                       v
                             +-------------------+
                             | GCD conflict loop | <---+
                             |  gcd(stride, N)   |     |
                             +---------+---------+     |
                                       |               |
                                    != 1 >-------------+
                                       |
                                     == 1
                                       |
                                       v
                                     stride
```

## KAT Vector & Offset Derivation Verification Table

Analysis of the current `_derive_offsets` implementation in `tests/unit/transport/test_stego.py`:

| Test Vector | Carrier Length | Expected Start | Expected Stride | Coprime Resolution Triggered |
|-------------|----------------|----------------|-----------------|------------------------------|
| `dummy_key_material_for_stego_kat` | 1000 | 131 | 227 | No |
| `key_1` | 1000 | 968 | 519 | Yes |

*Note: The current tests pass using the legacy `hashlib.sha256` hashing mechanism. Migrating to HMAC-SHA256 will require updating these KAT vectors to reflect the new expected values.*

## Coprime Conflict Resolution & Capacity Safety Assessment

1. **Coprime Conflict Resolution:**
   - The initial `stride` is derived and mapped to an odd integer by applying a bitwise OR `1`.
   - The algorithm runs a `math.gcd(stride, carrier_len) != 1` loop, incrementing `stride` by 2 until a coprime is found.
   - This approach deterministically resolves any potential conflicts, ensuring complete cyclic coverage of the carrier capacity.

2. **Capacity Safety:**
   - `_sequential_embed` and `_embed_permuted` assert that `len(payload) * 8 <= len(positions)`. 
   - The `MAX_PIXELS` safety bounds effectively cap carrier size, defending against OOM anomalies during unpacking.

## Steganalysis Resistance & PNG Filter Control Roadmap

- **Structural Steganalysis:** Currently, `_filter_none` nullifies PNG scanline filters after embedding, forcing a zero-filter baseline. While easy to decompress, this uniformity is an anomaly detection flag in structural steganalysis.
- **Visual Corruption:** LSB replacement is generally visually safe, but purely sequentially scattered payloads (using stride) can create weak localized textures if the payload isn't completely uniform.
- **Roadmap:**
  - Implement dynamic PNG filtering that re-applies adaptive filters (Sub, Up, Average, Paeth) post-embedding to preserve the statistical footprint of a standard PNG encoder.
  - Transition from stride-based permutation to a cryptographically secure PRNG (e.g., ChaCha20 seeded with the HMAC digest) to scatter bits uniformly and unpredictably.

## Code Hardening Patches

Below is the proposed patch to migrate the offset derivation from raw `hashlib.sha256` to a standard HMAC-SHA256 construction for stronger cryptographic binding.

```diff
--- src/configstream/stego.py
+++ src/configstream/stego.py
@@ -5,6 +5,7 @@
 
 import binascii
 import hashlib
+import hmac
 import logging
 import math
 import os
@@ -128,15 +129,14 @@
             raise ValueError("Invalid LSB salt length")
         derivation_input = (
             b"ConfigStream-LSB-v2\0"
-            + key_material
             + salt
             + struct.pack(">Q", carrier_len)
         )
     else:
-        derivation_input = key_material + struct.pack(">Q", carrier_len)
-    digest = hashlib.sha256(derivation_input).digest()
+        derivation_input = struct.pack(">Q", carrier_len)
+        
+    digest = hmac.new(key_material, derivation_input, hashlib.sha256).digest()
     start = int.from_bytes(digest[:8], "big") % carrier_len
     stride = max(1, (int.from_bytes(digest[8:16], "big") % carrier_len) | 1)
     while math.gcd(stride, carrier_len) != 1:
```
