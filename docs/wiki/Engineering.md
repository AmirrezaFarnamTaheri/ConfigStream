# Engineering Details

## Pareto Sorting
We don't just sort by Latency. A 50ms proxy that fails 50% of the time is worse than a 200ms proxy that never fails.
We use a multi-objective sort (currently approximated via weighted score until history DB is fully mature):
*   **Latency:** 50% weight
*   **Reliability:** 30% weight (Success Rate)
*   **Stability:** 20% weight (Jitter / Uptime)

## Deduplication
Proxies are often "fake unique" (same server, different remark/ID).
We generate a **Composite Fingerprint**:
`Hash(IP + Port + Protocol + TransportParams)`
If two proxies have the same fingerprint, we keep only the one with the highest Score.

## Atomic Writes
To prevent users from downloading half-written JSON files during a pipeline run, we use the `AtomicFileWriter`.
1.  Write data to `file.json.tmp`.
2.  `fsync` to ensure data is on disk.
3.  `os.rename` (atomic on POSIX) to replace `file.json`.

## WASM Tester
*   **Language:** Go (compiled to `wasm`)
*   **Interface:** Exposed via `window.checkProxy(config)`
*   **Limitations:** Browsers restrict raw TCP sockets. The WASM tester currently uses WebSocket or HTTP-based connectivity checks (or relies on a relay if configured). *Note: This is an experimental feature.*

## Static Vector Search
We implemented a "Zero-Cost" similarity search. Instead of paying for OpenAI embeddings or a Milvus instance:
1.  **Hashing:** We hash categorical features (Protocol, Country, ISP) into integer buckets.
2.  **Bucketing:** We bucket continuous features (Latency, Port) into ordinal groups.
3.  **Vector:** `[ProtoHash, CountryHash, LatencyBucket, ...]` (8 dimensions).
4.  **Search:** The frontend calculates Euclidean distance or Cosine similarity between these lightweight vectors in real-time.
