# 04. Engineering & Internals

This document is a deep dive into the algorithms, intelligence components, and chain-building systems that power ConfigStream.

> **Analogy**: If [02-architecture.md](02-architecture.md) is the blueprint of a factory, this document is the engineering manual for every machine inside it — how the sorting conveyor works, how the quality inspector thinks, how the chain-welding robot selects materials.

---

## 1. The Pareto Sort Algorithm

Most aggregators sort by Latency (Ping) alone. This is flawed because a proxy that pings 50ms but fails 50% of requests is useless. We use a multi-objective sorting algorithm inspired by [Pareto optimality](https://en.wikipedia.org/wiki/Pareto_efficiency).

### The Formula

```python
Score = (NormalizedLatency * 0.5) + (FailureRate * 0.3) + (Unstability * 0.2)
```

| Factor | Weight | Calculation | Example |
|---|---|---|---|
| **Normalized Latency** | 50% | `RawLatency / 1000`, capped at 1.0 | 100ms → `0.1`, 2000ms → `1.0` |
| **Failure Rate** | 30% | `1.0 - (Successes / TotalChecks)` | 100% success → `0.0`, 50% → `0.5` |
| **Unstability / Jitter** | 20% | `1.0 - Uptime` | 99% uptime → `0.01`, 70% → `0.30` |

**Result**: The sorting key minimizes the Score. A fast, reliable proxy appears at the top. A fast but broken proxy is pushed down.

> **Analogy**: Imagine hiring employees. You wouldn't hire someone who shows up on time (low latency) but only completes half their tasks (high failure rate). Pareto Sort considers the whole picture.

---

## 2. Adaptive Timeout

**File**: `src/configstream/intelligence/adaptive_timeout.py`

Fixed timeouts are inefficient — too short drops valid slow proxies (false negatives), too long wastes minutes on dead ones. The `AdaptiveTimeout` class tracks the average response time for every **Domain/IP** and adjusts dynamically.

### Algorithm

1.  **Cold Start**: Unknown hosts start at 10s.
2.  **Learning**: Every request records latency (success and failure) into an exponential moving average.
3.  **Calculation**: `TargetTimeout = p95_latency * 2`, smoothed to avoid spikes.
4.  **Bounds**: Min 3s, Max 30s.

| Host Example | Typical Latency | Calculated Timeout |
|---|---|---|
| `raw.githubusercontent.com` | 95-120ms | ~3s |
| `some-telegram-mirror.ir` | 8-12s | ~25s |
| Dead host (all timeouts) | — | [CircuitBreaker](#3-circuit-breaker) opens |

**Effect**: Speeds up the pipeline by 40-60% compared to fixed timeouts. If `us.server.com` usually responds in 200ms, we set the timeout to ~350ms. If it hangs, we cut it instantly.

> **Analogy**: A waiter who knows regular customers. "Table 3 always orders in 2 minutes, so I'll check back in 3. Table 7 takes 15 minutes to decide, so I'll give them 20."

---

## 3. Circuit Breaker

**File**: `src/configstream/intelligence/circuit_breaker.py`

Prevents the pipeline from wasting time on dead sources. After 3 consecutive failures, the breaker "opens" and all requests to that host are skipped instantly (no network I/O) for a 5-minute cooldown.

```
CLOSED (normal) → 3 failures → OPEN (skip all requests)
                                    ↓ cooldown expires
                               HALF-OPEN (try one request)
                                    ↓ success → CLOSED
                                    ↓ failure → OPEN again
```

Without this, the pipeline would spend 30+ seconds per dead source × dozens of dead sources = minutes wasted every run. With the breaker, dead sources are skipped in microseconds.

> **See also**: [Security Concepts — Circuit Breaker](../encyclopedia/glossary/security_concepts.md) for the general pattern and its [Fail-Open](../encyclopedia/glossary/security_concepts.md) behavior in ConfigStream.

---

## 4. The SingBoxTester

The `SingBoxTester` (`src/configstream/testers/manager.py`) is the interface between Python and the testing engines.

```python
if protocol in ["http", "socks"]:
    return self._test_direct(proxy)  # Uses aiohttp — no binary needed
elif self.go_tester.available:
    return self.go_tester.test_batch(batch)  # Go Sidecar — fast, preferred
else:
    return self._test_via_singbox(proxy)  # Sing-box subprocess — fallback
```

### The Go Sidecar (Batch Tester)

*   **Path**: `src/go/tester/main.go`
*   **Concurrency**: Uses Go routines. Can handle 500 concurrent checks easily.
*   **Interface**: NDJSON stream (one JSON object per line) for both stdin and stdout. Python writes proxy configs to stdin; Go writes test results to stdout.
*   **Payload Format**: Each `config` field must be a JSON **array** of outbounds (not a single object).
*   **Honeypot Check**: When `strict_security` is enabled, the Go sidecar performs a UDP honeypot probe and, if `CANARY_URL` is set, uses it as the test target. Otherwise, falls back to `TEST_URLS`.
*   **Evasion in Testing**: The tester applies [evasion features](../../CENSORSHIP_EVASION.md) during testing to avoid false negatives — a proxy that only works *with* uTLS will be correctly identified as working.

---

## 5. Pipeline Orchestration & Backpressure

The `run_full_pipeline` function (`src/configstream/pipeline.py`) orchestrates producer/consumer stages, concurrency tuning, and output generation.

*   **Work Queue**: `asyncio.Queue` with **max size 5000** — provides buffering between fetcher and tester without risking deadlocks under high load.
*   **Timeouts**: Consumers terminate only on sentinel values (no hard timeout) to avoid dropping slow sources.
*   **Event Stream Lifecycle**: Closed in a `finally` block to guarantee file handles and buffers are flushed even on exceptions.

### BoundedConcurrencyManager

To prevent "thundering herd" problems and OOM kills, we use a custom `BoundedConcurrencyManager`:

*   Uses an `asyncio.Condition` to manage a pool of permits.
*   **Dynamic Resizing (AIMD)**: If the error rate spikes (server overload or rate limiting), concurrency is reduced multiplicatively. If errors drop, it increases additively. This is the same [Additive Increase / Multiplicative Decrease](https://en.wikipedia.org/wiki/Additive_increase/multiplicative_decrease) algorithm that TCP uses for congestion control.

> **Analogy**: A highway toll booth that opens more lanes when traffic is smooth and closes lanes when there are accidents — preventing pile-ups while maximizing throughput.

---

## 6. Intelligence Layers

### Source Quality Tracker (`src/configstream/source_quality.py`)

Tracks the historical performance of every subscription source across runs.

| Rating | Criteria | Action |
|---|---|---|
| **Gold** | High reliability + High ASN diversity | Fetched first, highest priority |
| **Silver** | Average reliability | Fetched if capacity allows |
| **Garbage** | <1% reliability over 10 runs | Disabled automatically |

*   **Reliability**: `working_proxies / fetched_proxies`
*   **Consistency**: Variance in reliability over the last 10 runs.
*   **Diversity**: How many unique ASNs (ISPs) does this source provide? A source with 50 proxies across 30 ASNs is more valuable than one with 50 proxies on 2 ASNs.

### Anomaly Detector (`src/configstream/anomaly.py`)

Detects "Pollution Attacks" or "Spam Batches" using volume-based statistics (MAD + Z-score). Uses a persistent SQLite connection with `threading.Lock` and WAL mode.

*   **Volume Spikes**: Detects large deviations from historical counts per source. A source that usually provides 200 proxies suddenly providing 5,000 is flagged.
*   **Volume Drops**: Logs significant drops but does not block sources (informational).
*   **Fail-Open**: Transient DB errors allow sources through rather than blocking the pipeline.
*   **Shutdown**: Must call `.close()` during pipeline shutdown to release the DB connection.

### Evasion Engine (`src/configstream/intelligence/evasion.py`)

Enriches [Sing-box outbounds](../encyclopedia/tools/singbox_configuration_guide.md) with four censorship evasion techniques. See [CENSORSHIP_EVASION.md](../../CENSORSHIP_EVASION.md) for the full reference.

| Technique | What It Does | Defeats |
|---|---|---|
| **uTLS Fingerprinting** | Replaces Go/Python TLS fingerprint with Chrome/Firefox/Safari | Protocol fingerprinting |
| **TLS Fragmentation** | Splits ClientHello into 100-200 byte fragments with random delays | Stateless [DPI](../encyclopedia/glossary/networking_terms.md) |
| **Multiplexing + Padding** | Bundles streams via h2mux with random padding bytes | Traffic analysis (packet size patterns) |
| **[ALPN](../encyclopedia/glossary/networking_terms.md) Rotation** | Alternates `h2`, `http/1.1`, `h2,http/1.1` per proxy | ALPN-based blocking |

### DNS Intelligence (`src/configstream/intelligence/dns_lists.py`)

Curated DNS lists used for routing decisions and output generation:

*   **Iran Infrastructure DNS** — Servers used by Iranian ISPs (e.g., `10.202.10.10`). Detects domestic traffic that should bypass the VPN.
*   **Cloudflare Optimized IPs** — Clean Cloudflare edge IPs for CDN-based transports and [WARP](../encyclopedia/networking/warp.md) endpoints.
*   **Fallback Resolvers** — DoH/DoT/DoQ resolvers (Cloudflare, Google, Quad9, AdGuard) embedded in DNS-hardened outputs.

---

## 7. Proxy Washing & Shielding

### ProxyWasher (`src/configstream/intelligence/washer/`)

Wraps proxies in Cloudflare [WARP](../encyclopedia/networking/warp.md) tunnels for three distinct purposes:

| Operation | Topology | Purpose |
|---|---|---|
| **Wash** | `Client → Proxy → WARP → Internet` | Hide proxy IP from destination (unblock Netflix/Google) |
| **Shield** | `Client → WARP → Proxy → Internet` | Hide proxy IP from ISP/censor (Copper → Gold) |
| **Revive** | Wrap dead proxy in WARP/Vwarp chain | Resurrect failed proxies |

**Candidate Selection**: When a WARP pool is configured, we wash **all working proxies** (not just those tagged `dirty_ip`), providing a safer default in case tagging fails upstream.

### Revival Process

1. Pipeline tests all proxies. Some fail.
2. Washer wraps each dead proxy in a WARP chain (and separately in a Vwarp chain).
3. Wrapped proxies are re-tested immediately.
4. Successes are tagged `revived-warp` or `revived-vwarp` and included in output.
5. Typically recovers 10-30% of dead proxies.

### WARP vs Vwarp

| | WARP | Vwarp |
|---|---|---|
| **Mechanism** | Cloudflare WARP keys via WireGuard configs | `vwarp` binary for tunnel management |
| **Requires** | `WARP_KEY_POOL` secret | `vwarp` binary (falls back to `WarpScraper` if missing) |
| **Logging** | Basic | Structured (timing, PID, failure classification) |
| **Failure Handling** | Retry | Classified into `config`, `dns`, `connectivity`, `other` for targeted retry |

---

## 8. Smart Chain Intelligence

**File**: `src/configstream/intelligence/chaining.py`

Generates multi-hop proxy chains optimized for different routing goals. Uses a scoring algorithm that considers geographic distance, protocol stealth/speed scores, and [censorship levels](../encyclopedia/security/firewall_honeypot.md).

### Geographic Coverage (95 Countries)

The chain builder knows the geographic coordinates and censorship level of 95 countries:

| Region | Count | Examples |
|---|---|---|
| **Middle East & Central Asia** | 15 | GE, UZ, KG, TJ, AF, PK, QA, OM, BH, KW, JO, LB, IL, SY, BY |
| **Asia-Pacific** | 12 | MY, TH, VN, ID, PH, IN, BD, LK, NP, MM, KH, LA |
| **Europe** | 23 | ES, PT, NO, DK, IE, AT, BE, CZ, RO, GR, BG, HR, RS, SK |
| **Americas** | 9 | MX, BR, AR, CL, CO, PE, EC, CR, PA |
| **Africa** | 10 | ZA, EG, NG, KE, MA, TN, DZ, GH, ET, UG |

### Protocol Scoring Matrix

Each protocol has stealth, speed, and reliability scores (0-10) plus a routing penalty in kilometers:

| Protocol | Stealth | Speed | Reliability | Penalty (km) |
|---|---|---|---|---|
| [VLESS](../encyclopedia/protocols/vless.md) | 10 | 7 | 8 | 0 |
| [Trojan](../encyclopedia/protocols/trojan.md) | 9 | 7 | 9 | 100 |
| [VMess](../encyclopedia/protocols/vmess.md) | 8 | 6 | 8 | 200 |
| [Hysteria2](../encyclopedia/protocols/hysteria2.md) | 6 | 10 | 7 | 0 |
| TUIC | 6 | 9 | 7 | 50 |
| [Shadowsocks](../encyclopedia/protocols/shadowsocks.md) | 7 | 8 | 9 | 200 |
| [WireGuard](../encyclopedia/protocols/wireguard.md) | 4 | 10 | 10 | 300 |
| SSH | 9 | 5 | 10 | 400 |

### Censorship Levels

| Level | Countries | Strategy |
|---|---|---|
| 10 | CN, IR, KP | Maximum stealth, multi-hop required |
| 9 | TM, SY | High stealth protocols |
| 7-8 | RU, BY, CU, SA | Stealth protocols recommended |
| 5-6 | TR, EG, VE, PK | Standard protocols acceptable |
| 0-4 | Most Western countries | All protocols available |

### Scoring Algorithm

```
Final Score = Base Distance + Protocol Penalty + Mode Penalty + Efficiency Penalty + Censorship Adjustment

Where:
  Base Distance = haversine(origin → relay) + haversine(relay → exit)
  Protocol Penalty = PROTOCOL_SCORES[protocol]["penalty_km"]
  Mode Penalty = f(optimization_mode, protocol_scores)
  Efficiency Penalty = {
    0 if path ≤ 1.5x direct,
    1000 if 1.5x < path ≤ 1.8x direct,
    2000 if path > 1.8x direct
  }
  Censorship Adjustment = {
    -300 if transitioning from high (≥7) → low (≤3) censorship,
    +200 if staying in similar censorship region
  }
```

> **Analogy**: Imagine planning a road trip. The scoring algorithm is like a GPS that considers not just distance (base), but also road quality (protocol penalty), speed limits (mode penalty), whether you're taking a huge detour (efficiency penalty), and whether you're crossing from a dangerous country into a safe one (censorship bonus).

### 9 Chain Types

| # | Type | Topology | Hops | Use Case |
|---|---|---|---|---|
| 1 | **Intranet** | IR relay → Foreign exit | 2 | Basic censorship circumvention |
| 2 | **Intranet Washed** | IR relay → Foreign exit → WARP | 3 | Enhanced privacy with WARP tunnel |
| 3 | **IPv6 Portal** | Dual-stack relay → IPv6-only exit | 2 | Access IPv6-only services |
| 4 | **Streaming** | Fast relay (Hysteria2/TUIC) → Streaming region | 2 | Low-latency streaming (Netflix, YouTube) |
| 5 | **Censorship Resistant** | Stealth relay (VLESS/Trojan) → Free region exit | 2 | Maximum DPI evasion |
| 6 | **Low Latency** | Speed-optimized relay → Nearby exit | 2 | Gaming, VoIP, real-time apps |
| 7 | **High Anonymity** | Asia → Europe → Americas (3-hop) | 3 | Maximum privacy, 3 jurisdictions |
| 8 | **Load Balanced** | Multiple paths to same destination | 2×3 | Failover resilience |
| 9 | **Experimental** | Fast relay → Standard exit | 2 | Protocol wrapping tests |

### Use Case Examples

**User in Iran (Heavy Censorship)**:
1. **Censorship Resistant**: IR → TR (VLESS) → DE — stealth protocol, transitions to low-censorship region.
2. **Intranet Washed**: IR → AE → WARP — 3-hop with WARP tunnel for enhanced privacy.

**User Wants Netflix Streaming**:
1. **Streaming**: SG (Hysteria2) → US — fast UDP protocol, low latency to streaming servers.
2. **Low Latency**: JP (TUIC) → US — speed-optimized scoring, minimal overhead.

**High-Threat Activist**:
1. **High Anonymity**: SG → DE → US — 3 jurisdictions, traffic correlation resistance.
2. **Censorship Resistant**: IR → TR (Trojan) → NL — stealth protocols, jurisdiction transition.

### Developer API

```python
from configstream.intelligence.chaining import generate_smart_chains

chains = generate_smart_chains(proxies, washer=None)

# Access by type
censorship_chains = chains["censorship_resistant"]
low_latency_chains = chains["low_latency"]
high_anon_chains = chains["high_anonymity"]
```

### Chain Generation Statistics

With 9 categories, the system typically generates 200-400 chains per run. With 100 working proxies (30 IR, 70 foreign), expect ~165-195 chains distributed across all types.

---

## 9. Static Vectors (Vector Search)

To enable "Natural Language Search" on a static site:
1.  **Vector Generation**: Convert proxy attributes (Country, City, ISP, Protocol, Speed Tag) into a low-dimensional vector using SHA-256-based feature hashing.
2.  **Pre-computation**: Generate `output/vectors.json` mapping `ProxyID -> [Vector]`.
3.  **Client-Side**: The frontend uses these vectors with basic metadata to compute keyword-based relevance scores (see [06-frontend.md](06-frontend.md)).
4.  **Future**: Cosine similarity over dense vectors in a Web Worker for semantic search on large datasets.

---

## 10. BYOW Subscription Generator

**File**: `tools/workers/subscription_worker.js`

A Cloudflare Worker that proxies VLESS traffic and serves dynamic subscription links for the user's private node. Supports Clash YAML, Sing-box JSON, and V2Ray Base64 formats. Deploy a single worker to get a full subscription endpoint for all clients at zero cost. See [CENSORSHIP_EVASION.md — BYOW](../../CENSORSHIP_EVASION.md) for the full deployment walkthrough.

---

## Related Documentation

*   **[Architecture Deep Dive](02-architecture.md)** — Pipeline flow, sharding, intelligence layer context.
*   **[Protocols & Parsing](03-protocols.md)** — How proxies are parsed before entering the testing/scoring pipeline.
*   **[Security & Privacy](07-security.md)** — Anomaly detection, blocklists, honeypot guard.
*   **[Censorship Evasion](../../CENSORSHIP_EVASION.md)** — Unified evasion reference (modes, techniques, DNS, shielding, BYOW).
*   **[Security Concepts](../encyclopedia/glossary/security_concepts.md)** — Circuit Breaker, Adaptive Timeout, Fail-Open patterns explained.
*   **[WARP & Clean IPs](../encyclopedia/networking/warp.md)** — Washing mechanics, key assignment, shielding topology.
*   **[Networking Terms](../encyclopedia/glossary/networking_terms.md)** — TLS, SNI, DPI, QUIC, ALPN — the building blocks referenced above.
*   **[Firewalls & Honeypots](../encyclopedia/security/firewall_honeypot.md)** — Censorship systems the chain builder is designed to defeat.
