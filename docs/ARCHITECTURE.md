# ConfigStream Architecture

This document provides a comprehensive overview of ConfigStream's architecture, design patterns, and implementation details.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Core Components](#core-components)
4. [Data Flow](#data-flow)
5. [Pipeline Architecture](#pipeline-architecture)
6. [Concurrency Model](#concurrency-model)
7. [Data Storage](#data-storage)
8. [Security Architecture](#security-architecture)
9. [Frontend Architecture](#frontend-architecture)
10. [Deployment Architecture](#deployment-architecture)
11. [Performance Optimizations](#performance-optimizations)
12. [Design Patterns](#design-patterns)
13. [Scalability Considerations](#scalability-considerations)

---

## System Overview

ConfigStream is an automated VPN configuration aggregator that collects, tests, and publishes working proxy configurations from free public sources. The system operates on a scheduled basis (every 6 hours) via GitHub Actions.

### Key Characteristics

- **Event-Driven**: Producer-consumer pattern with async/await
- **Highly Concurrent**: Up to 500 parallel proxy tests
- **Resilient**: Circuit breakers, retries, graceful degradation
- **Zero-Cost**: Uses free tiers of GitHub Actions, Pages, GeoIP
- **Stateless**: Each pipeline run is independent
- **Observable**: Real-time WebSocket feeds, comprehensive logging

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        GITHUB ACTIONS                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Scheduler (Every 6 Hours)                                 │ │
│  └────────────────┬───────────────────────────────────────────┘ │
└───────────────────┼──────────────────────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────────────────────┐
│                    CONFIGSTREAM PIPELINE                          │
│                                                                   │
│  ┌──────────────┐     ┌────────────────┐     ┌───────────────┐ │
│  │   FETCHER    │────▶│    PARSER      │────▶│  VALIDATOR    │ │
│  │              │     │                │     │               │ │
│  │ • HTTP/2     │     │ • 25+ Protocols│     │ • Security    │ │
│  │ • Retries    │     │ • Auto-detect  │     │ • Blocklist   │ │
│  │ • Caching    │     │ • Normalization│     │ • Sanitization│ │
│  └──────────────┘     └────────────────┘     └───────┬───────┘ │
│                                                        │         │
│  ┌────────────────────────────────────────────────────▼──────┐  │
│  │                     TEST QUEUE                            │  │
│  │  (asyncio.Queue, in-memory, bounded size)      │  │
│  └────────────────────────────────────────────────────┬──────┘  │
│                                                        │         │
│  ┌─────────────────────────────────────────────────────▼──────┐ │
│  │                   CONCURRENT TESTER                        │ │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐        │ │
│  │  │Worker│  │Worker│  │Worker│  │Worker│  │Worker│ × N     │ │
│  │  └───┬──┘  └───┬──┘  └───┬──┘  └───┬──┘  └───┬──┘        │ │
│  │      │         │         │         │         │            │ │
│  │      └─────────┴─────────┴─────────┴─────────┘            │ │
│  │                        │                                   │ │
│  │              ┌─────────▼───────────┐                       │ │
│  │              │  GO BATCH ENGINE    │                       │ │
│  │              │  (High Performance) │                       │ │
│  │              └─────────────────────┘                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                        │         │
│  ┌────────────────────────────────────────────────────▼──────┐  │
│  │             INTELLIGENCE & POST-PROCESSING                 │  │
│  │  • GeoIP      • Scoring     • Anomaly Detection           │  │
│  │  • Proxy Washing (WARP)     • Chain Synthesis             │  │
│  └────────────────────────────────────────────────────┬──────┘  │
│                                                        │         │
│  ┌────────────────────────────────────────────────────▼──────┐  │
│  │                   OUTPUT GENERATION                        │  │
│  │  • Base64  • Clash  • Sing-box  • Shadowrocket           │  │
│  │  • Surge  • Loon  • Quantumult X  • SIP008               │  │
│  │  • Side Products: OpenVPN, WireGuard, Plain URIs (ZIP)   │  │
│  │  • Washed Chains  • Smart Routing  • Smart Chains        │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬────────────────────────────────┘
                                   │
┌──────────────────────────────────▼────────────────────────────────┐
│                        GITHUB PAGES                                │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Frontend (PWA)    │    API Endpoints    │   Static Files  │   │
│  │  • Dashboard       │    • /api/proxies   │   • output/*    │   │
│  │  • Analytics       │    • /api/stats     │   • frontend/*  │   │
│  │  • Live Feed       │    • /subscribe/*   │                 │   │
│  └────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Fetcher (`fetcher.py`)

**Responsibility**: Retrieve proxy configurations from remote sources

**Key Features**:
- HTTP/2 support with connection pooling
- Exponential backoff retries (max 3)
- Adaptive timeouts with jitter tracking
- Rate limiting protection
- Circuit breaker pattern
- Binary-safe streaming (aiter_bytes + safe decode)

**Implementation**:
```python
async def fetch_multiple_sources(
    sources: List[str],
    timeout: float,
    concurrency_controller: ConcurrencyManager
) -> Dict[str, FetchResult]:
    # Parallel fetching with controlled concurrency
    # Returns FetchResult with content, status, timing
```

**Dependencies**:
- `httpx`: Modern async HTTP client
- `ConcurrencyManager`: Adaptive concurrency control
- `CircuitBreaker`: Failure isolation

---

### 2. Parser (`parsers.py`)

**Responsibility**: Parse and normalize proxy configurations

**Supported Protocols** (26+):
- VMess, VLESS, Shadowsocks, SS2022, Trojan, Hysteria 2
- TUIC, Wireguard, Juicity, SSH, SOCKS5, HTTP, OpenVPN, SSR
- Auto-detection for unlabeled configs

**Implementation**:
```python
def parse_proxy(config_str: str) -> Optional[Proxy]:
    """
    1. Detect protocol (ss://, vmess://, vless://, etc.)
    2. Decode Base64 if needed
    3. Parse JSON/URI format
    4. Normalize fields
    5. Generate stable ID
    6. Validate security constraints
    """
```

**Key Functions**:
- **Protocol Detection**: Regex + magic bytes
- **Base64 Decoding**: Handles various padding
- **JSON Parsing**: Nested config structures
- **URI Parsing**: Query string extraction
- **Validation**: Port ranges (1-65535), cipher support, hostname format
- **Security**: Input size limits (1MB for OpenVPN), injection prevention

---

### 3. Validator (`security_validator.py`)

**Responsibility**: Security validation before testing

**Checks**:
1. **IP Blocklist**: Private networks, TOR exit nodes, honeypots
2. **DNS Rebinding**: Prevent localhost redirects
3. **Port Blocklist**: Dangerous ports (22, 23, 3389)
4. **Config Sanitization**: Trace ID validation

**Implementation**:
```python
def validate_batch_configs(
    proxies: List[Proxy],
    policy: SecurityPolicy
) -> List[Proxy]:
    """Filter proxies through security checks"""
```

---

### 4. Tester (`testers.py` & `src/go/tester`)

**Responsibility**: Test proxy functionality

**Architecture**:
- **Go Batch Tester**: High-performance binary for concurrent testing
- **Sing-box Core**: Used as the underlying engine

**Test Flow**:
1. **Batching**: Python pipelines batches of proxies to Go binary
2. **Connectivity**: Test URLs (Google, Cloudflare)
3. **Latency**: Precise measurement
4. **Security Tests**: Honeypot detection (Active/Passive)
5. **Retry Logic**: Robust port binding retry loop in Go

**Implementation**:
```go
// Go implementation
func setupSingbox(ctx context.Context, outboundJSON string) (*box.Box, int, error) {
    // Retry loop for port race conditions
    for i := 0; i < MaxRetries; i++ {
        // ... bind port 0 ...
    }
}
```

**Key Features**:
- **Process Isolation**: Each proxy gets separate sing-box instance
- **Race Condition Prevention**: Retry loops for port binding
- **Deadlock Prevention**: Async timeouts in Python wrapper
- **Resource Cleanup**: Guaranteed process termination

---

### 5. Intelligence Engine (`intelligence/washer.py`)

**Responsibility**: Enhance proxy quality and security

**Features**:
1. **Proxy Washing & Revival**: Wraps flagged/dirty proxies AND revives dead/non-working proxies by chaining them through Cloudflare WARP (WireGuard).
2. **Washer Retest**: Ensures end-to-end connectivity of generated chains by feeding them back into the tester.
3. **Smart Chaining**: Creates routing chains (e.g., Intranet Bridge, IPv6 Portal)
4. **Consistent Hashing**: Deterministic exit node selection (Key Rotation).

**Implementation**:
```python
class ProxyWasher:
    def wash_batch(self, proxies: List[Proxy]) -> Tuple[List[Dict], Set[str]]:
        """
        Identify candidates (working & non-working) and wrap them in WireGuard chains.
        Returns cleaned chains and IDs of washed proxies.
        """
```

---

### 6. GeoIP Resolver (`geoip.py`)

**Responsibility**: Enrich proxies with geographic data

**Data Sources**:
- MaxMind GeoLite2 City (offline)
- MaxMind GeoLite2 ASN (offline)

**Implementation**:
```python
# [v2.2.0 Update] Thread-safe Singleton with Hot-Reloading
def lookup(ip: str) -> GeoData:
    """
    1. Check if DB file changed (mtime check) -> Reload if needed
    2. Acquire Lock (Thread-safe read)
    ...
    """
    """
    1. Validate IP format
    2. Query GeoLite2-City.mmdb
    3. Query GeoLite2-ASN.mmdb
    4. Return GeoData(country_code, city, asn, org)
    """
```

**Features**:
- Zero API calls (offline databases)
- Sub-millisecond lookups
- Automatic fallbacks

---

### 7. Scorer (`score.py`)

**Responsibility**: Rank proxies by multiple criteria

**Scoring Algorithms**:

1. **Balanced Score** (Default)
   ```
   Score = (latency_weight × 0.4) +
           (security_weight × 0.3) +
           (stability_weight × 0.3)
   ```

2. **Speed Score**
   ```
   Score = 100 - (latency / soft_cap × 50)
   ```

3. **Privacy Score** (Conceptual)
   > Design pattern only – not wired into the default pipeline yet.
   ```
   Score = (security_checks × 30) +
           (no_logs_asn × 20) +
           (protocol_strength × 50)
   ```

4. **Stability Score**
   ```
   Score = (uptime_history × 40) +
           (low_jitter × 30) +
           (consistent_speed × 30)
   ```

**Implementation**:
```python
def calculate_balanced_score(proxy: Proxy) -> float:
    """Multi-dimensional scoring"""
```

---

### 8. Output Generator (`output.py` & `adapters.py`)

**Responsibility**: Generate subscription files and native protocol exports

**Output Formats**:
- Base64 subscription URLs
- Clash YAML
- Sing-box JSON (including Washed chains & Smart chains)
- Surge conf (supports WireGuard-over-Proxy & Smart chains)
- Loon conf (supports WireGuard-over-Proxy & Smart chains)
- Quantumult X (with Smart chains)
- Shadowrocket (with Smart chains)
- SIP008 JSON

**Side Products** (Native Protocol Exports):
- **OpenVPN**: Individual `.ovpn` files for direct import
- **WireGuard**: Individual `.conf` files for WireGuard clients
- **Plain URIs**: Protocol-grouped text files (VMess, VLess, etc.)
- **ZIP Archive**: Complete package with README and all side products

**Key Features**:
- **Atomic Writes**: Temp file + rename
- **Compression**: Gzipped variants
- **Metadata**: JSON with statistics (sources_count, vwarp efficiency)
- **Split-Brain Prevention**: Centralized washing logic
- **Country Splits**: Separate files per country
- **Smart Chains**: Topology-aware chains in all adapters

---

## Data Flow

### Pipeline Execution Flow

```
┌────────────┐
│   START    │
└─────┬──────┘
      │
      ▼
┌─────────────────────┐
│  Load Sources List  │
└─────────┬───────────┘
          │
          ▼
┌──────────────────────────┐
│  Source Producer Task    │◀────┐
│  (Async iterator)        │     │
└──────────┬───────────────┘     │
           │                     │
           │  emit source URL    │
           ▼                     │
      ┌────────────┐             │
      │Work Queue  │             │
      │(Bounded)   │             │
      └─────┬──────┘             │
            │                    │
            ▼                    │
┌────────────────────────────┐  │
│  Processing Consumer Task  │  │
│  (Runs until queue empty)  │  │
└─────────┬──────────────────┘  │
          │                     │
          │  For each source:   │
          ▼                     │
    ┌──────────┐                │
    │  FETCH   │                │
    └────┬─────┘                │
         │                      │
         ▼                      │
    ┌──────────┐                │
    │  PARSE   │                │
    └────┬─────┘                │
         │                      │
         ▼                      │
    ┌──────────┐                │
    │ VALIDATE │                │
    └────┬─────┘                │
         │                      │
         ▼                      │
    ┌──────────┐                │
    │CACHE CHK │───▶(cached)────┤
    └────┬─────┘                │
         │ (miss)               │
         ▼                      │
    ┌──────────┐                │
    │  TEST    │                │
    │(Parallel)│                │
    └────┬─────┘                │
         │                      │
         ▼                      │
    ┌──────────┐                │
    │ GEOIP    │                │
    └────┬─────┘                │
         │                      │
         ▼                      │
    ┌──────────┐                │
    │  SCORE   │                │
    └────┬─────┘                │
         │                      │
         ▼                      │
    ┌──────────┐                │
    │  FILTER  │                │
    └────┬─────┘                │
         │                      │
         │  Accumulate results  │
         └──────────────────────┘
                 │
                 ▼
      ┌─────────────────────┐
      │  All sources done?  │
      └─────────┬───────────┘
                │ YES
                ▼
      ┌─────────────────────┐
      │  DEDUPLICATE        │
      │  (by IP:Port)       │
      └─────────┬───────────┘
                │
                ▼
      ┌─────────────────────┐
      │  INTELLIGENCE       │
      │  (Wash & Chain)     │
      └─────────┬───────────┘
                │
                ▼
      ┌─────────────────────┐
      │  GENERATE OUTPUTS   │
      │  (all formats)      │
      └─────────┬───────────┘
                │
                ▼
      ┌─────────────────────┐
      │  ATOMIC WRITE       │
      │  (temp + rename)    │
      └─────────┬───────────┘
                │
                ▼
      ┌─────────────────────┐
      │  GIT COMMIT + PUSH  │
      └─────────┬───────────┘
                │
                ▼
           ┌────────┐
           │  DONE  │
           └────────┘
```

---

## Pipeline Architecture

### Producer-Consumer Pattern

```python
# Simplified architecture
async def run_full_pipeline():
    work_queue = asyncio.Queue(maxsize=10000)

    async def _source_producer():
        for source in sources:
            if quality_tracker.should_fetch(source):
                await work_queue.put(source)
        await work_queue.put(None)  # Sentinel

    async def _processing_consumer():
        while True:
            source = await work_queue.get()
            if source is None:
                break

            # Process source
            proxies = await fetch_and_parse(source)
            tested = await test_batch(proxies)
            enriched = await enrich_with_geoip(tested)

            final_proxies.extend(enriched)
            work_queue.task_done()

    # Run concurrently
    await asyncio.gather(
        _source_producer(),
        _processing_consumer()
    )
```

### Backpressure Control

When queue fills up (`maxsize` reached), producer blocks until consumer catches up:

```
Producer ─────▶ Queue (10000) ─────▶ Consumer
                   │
                   ▼
               [FULL] ───▶ Producer waits
```

---

## Concurrency Model

### Adaptive Concurrency (AIMD)

ConfigStream uses Additive Increase Multiplicative Decrease (AIMD) to dynamically adjust workers:

```python
class ConcurrencyManager:
    def _adjust(self):
        error_rate = errors / total_requests

        if error_rate > 0.1:
            # Multiplicative Decrease
            new_limit = current_limit × 0.7
        elif error_rate < 0.01:
            # Additive Increase
            new_limit = current_limit + 5
```

### Semaphore-Based Limiting

```python
async with concurrency.get_semaphore():
    # Only N concurrent operations allowed
    result = await test_proxy(proxy)
```

### Thread Safety

All shared data structures use appropriate locks:

```python
# For async operations: asyncio.Lock
async with self._async_state_lock:
    self._clean_ips = fresh_endpoints
    self._warp_keys = new_keys

# For sync operations: threading.Lock
with self._state_lock:
    return self._warp_keys[:]
```

**Critical Fix (v2.0.12)**: Added separate `asyncio.Lock` for async operations in ProxyWasher to prevent race conditions when concurrent async tasks access shared state. Previously, only `threading.Lock` was used, which doesn't protect async operations.

---

## Data Storage

### SQLite Databases

**1. Source Quality DB** (`data/source_quality.db`)
- `source_stats` (reliability, consecutive failures, trust score)
- `source_runs` (per-run metrics)
- `proxy_history` (per-proxy test history)

**2. Proxy History DB** (`data/history.db`)
- Same schema as above when a separate history DB is used

### JSON Caches

- `data/test_cache.json`: recent proxy test results (TTL cache)
- `data/timeout_history.json`: adaptive timeout state

### GeoIP Data

- `data/GeoLite2-City.mmdb` and `data/GeoLite2-ASN.mmdb`

### Schema Examples

```sql
CREATE TABLE source_stats (
    url TEXT PRIMARY KEY,
    total_fetched INTEGER DEFAULT 0,
    total_working INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    last_checked INTEGER DEFAULT 0,
    reliability_score REAL DEFAULT 100.0,
    diversity_score REAL DEFAULT 0.0,
    trust_score REAL DEFAULT 50.0,
    status TEXT DEFAULT 'active'
);

CREATE TABLE proxy_history (
    proxy_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    is_working INTEGER NOT NULL,
    latency REAL,
    country_code TEXT,
    session_id TEXT,
    failure_reason TEXT
);
```

### Write-Ahead Logging (WAL)

```python
conn.execute("PRAGMA journal_mode=WAL")
```

**Benefits**:
- Concurrent readers + single writer
- Better crash recovery
- Reduced lock contention

---

## Security Architecture

### Defense in Depth

```
User Request
    │
    ▼
┌─────────────────────┐
│  Rate Limiting      │ ◀── 100 req/min per IP
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Input Sanitization │ ◀── Trace ID validation
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  IP Blocklist       │ ◀── Private networks, TOR
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  DNS Rebinding Chk  │ ◀── Localhost redirects
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Port Filtering     │ ◀── Dangerous ports
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Proxy Testing      │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Security Checks    │
│  • MITM Detection   │
│  • HTML Injection   │
│  • Header Tamper    │
│  • Honeypot Check   │
└─────────────────────┘
```

### Security Modules

**1. Blocklist (`security/blocklist.py`)**
- 5000+ malicious IP ranges (CIDR)
- Known honeypot ASNs
- TOR exit nodes

**2. Honeypot Detector (`security/honeypot.py`)**
- Connects to various ports
- Detects banner injection
- Identifies trap servers

**3. uTLS Wrapper (`security/utls_wrapper.py`)**
- Randomizes TLS fingerprints
- Prevents browser fingerprinting
- Go-based sidecar

**4. SS-FFI (`security/ss_ffi.py`)**
- Validates Shadowsocks configs
- Uses official Rust implementation
- FFI boundary protection

---

## Frontend Architecture

### Progressive Web App (PWA)

**Technology Stack**:
- Vanilla JavaScript (no frameworks)
- Chart.js for visualizations
- Globe.gl for 3D map
- DataTables for proxy list
- WebSocket for live updates

**Components**:

1. **Dashboard** (`index.html`)
   - Proxy count cards
   - Live activity feed
   - Quick stats

2. **Proxy Browser** (`proxies.html`)
   - Searchable, sortable table
   - Advanced filtering
   - Export functionality

3. **Analytics** (`analytics.html`)
   - Protocol distribution chart
   - Latency histogram
   - Geographic heatmap
   - Top countries ranking

4. **3D Globe** (`assets/js/globe.js`)
   - Interactive world map
   - Proxy location markers
   - Real-time data binding

### WebSocket Architecture

```
┌─────────────┐          ┌──────────────┐
│  Frontend   │ ◀───WS───▶│   Server     │
└─────────────┘          └───────┬──────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │  EventStream  │
                         │   (Singleton) │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │  Log Tailer   │
                         │ (real-time)   │
                         └───────────────┘
```

**Message Format**:
```json
{
  "type": "fetch|parse|test|geo|score",
  "timestamp": "2025-11-21T10:30:00Z",
  "message": "Testing proxy: ss://...",
  "data": {...}
}
```

---

## Deployment Architecture

### GitHub Actions (CI/CD)

```
┌──────────────────────────────────────────────────────────┐
│               GITHUB ACTIONS WORKFLOW                     │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Trigger: Cron (*/6 * * * *) or Manual            │  │
│  └────────────────────────────────────────────────────┘  │
│                          │                               │
│  ┌───────────────────────▼────────────────────────────┐  │
│  │  Job: Build                                        │  │
│  │  • Checkout code                                   │  │
│  │  • Setup Python 3.11                               │  │
│  │  • Install dependencies                            │  │
│  │  • Download GeoIP databases                        │  │
│  └────────────────────────────────────────────────────┘  │
│                          │                               │
│  ┌───────────────────────▼────────────────────────────┐  │
│  │  Job: Test                                         │  │
│  │  • Run pytest                                      │  │
│  │  • Check code quality (black, flake8)             │  │
│  │  • Upload coverage report                          │  │
│  └────────────────────────────────────────────────────┘  │
│                          │                               │
│  ┌───────────────────────▼────────────────────────────┐  │
│  │  Job: Process (Matrix: batch 1-11)                 │  │
│  │  • Run pipeline for batch_N.txt                   │  │
│  │  • Test proxies (parallel)                        │  │
│  │  • Upload shard artifact                          │  │
│  └────────────────────────────────────────────────────┘  │
│                          │                               │
│  ┌───────────────────────▼────────────────────────────┐  │
│  │  Job: Merge                                        │  │
│  │  • Download all shard artifacts                    │  │
│  │  • Merge results                                   │  │
│  │  • Deduplicate by IP:Port                          │  │
│  │  • Sort by score                                   │  │
│  └────────────────────────────────────────────────────┘  │
│                          │                               │
│  ┌───────────────────────▼────────────────────────────┐  │
│  │  Job: Generate                                     │  │
│  │  • Generate all output formats                     │  │
│  │  • Create metadata.json                            │  │
│  │  • Optimize images                                 │  │
│  └────────────────────────────────────────────────────┘  │
│                          │                               │
│  ┌───────────────────────▼────────────────────────────┐  │
│  │  Job: Deploy                                       │  │
│  │  • Git commit (if changes)                         │  │
│  │  • Git push to main                                │  │
│  │  • GitHub Pages auto-deploys                       │  │
│  └────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

### Sharding Strategy

**Problem**: Single job would timeout (6-hour limit)

**Solution**: Matrix strategy (11 parallel jobs)

```yaml
strategy:
  matrix:
    batch: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
```

**Benefits**:
- 6× faster execution
- Fault isolation (one batch fails, others continue)
- Better resource utilization

---

## Performance Optimizations

### 1. Connection Pooling

```python
client = httpx.AsyncClient(
    http2=True,
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    )
)
```

### 2. DNS Caching

```python
@lru_cache(maxsize=10000)
def resolve_dns(hostname: str) -> str:
    return socket.gethostbyname(hostname)
```

### 3. Lazy Logging

```python
logger.debug("Proxy %s failed", proxy.id)  # String not formatted unless DEBUG
```

### 4. Bounded Caches

```python
self.latencies: Deque[float] = deque(maxlen=100)  # Auto-evict oldest
```

### 5. Chunked Processing

```python
for i in range(0, len(proxies), chunk_size):
    chunk = proxies[i:i + chunk_size]
    results = await asyncio.gather(*[test(p) for p in chunk])
```

### 6. Smart Deduplication with Memory Management

```python
# [v2.0.12 FIX] Efficient deduplication with bounded memory
max_seen = int(os.getenv("MAX_SEEN_KEYS", "200000"))

for proxy in parsed_batch:
    key = proxy_unique_key(proxy)
    if key not in seen_keys:
        # Only evict when approaching limit
        if len(seen_keys) >= max_seen:
            eviction_count = max(1000, max_seen // 10)
            keys_to_remove = list(seen_keys)[:eviction_count]
            seen_keys.difference_update(keys_to_remove)

        seen_keys.add(key)
        unique_batch.append(proxy)
```

**Improvement**: Previous implementation used crude batch eviction that created full list copies, causing memory spikes. New implementation only evicts when at capacity and uses `difference_update()` for efficiency.

### 7. Memory Slots

```python
@dataclass
class Proxy:
    __slots__ = ('protocol', 'address', 'port', ...)  # 40% memory savings
```

---

## Design Patterns

### 1. Singleton (GeoIP Resolver)

```python
_geoip_instance = None

def get_geoip_resolver():
    global _geoip_instance
    if _geoip_instance is None:
        _geoip_instance = GeoIPResolver()
    return _geoip_instance
```

### 2. Factory (Adapter Pattern)

```python
def get_adapter(format: str) -> BaseAdapter:
    adapters = {
        'clash': ClashAdapter,
        'singbox': SingboxAdapter,
        'surge': SurgeAdapter,
    }
    return adapters[format]()
```

### 3. Strategy (Scoring Algorithms)

```python
class BalancedScorer:
    def score(self, proxy): ...

class SpeedScorer:
    def score(self, proxy): ...

scorer = BalancedScorer()  # or SpeedScorer()
score = scorer.score(proxy)
```

### 4. Observer (Event Stream)

```python
class EventStream:
    def emit(self, event):
        for listener in self._listeners:
            listener.on_event(event)
```

### 5. Circuit Breaker

```python
class CircuitBreaker:
    def call(self, func):
        if self.is_open():
            raise CircuitOpenError

        try:
            result = func()
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise
```

---

## Scalability Considerations

### Horizontal Scaling

**Current**: Single GitHub Actions runner
**Future**: Multiple runners with sharding

```
Runner 1 ────▶ Batch 1-2
Runner 2 ────▶ Batch 3-4
Runner 3 ────▶ Batch 5-6
       │
       └────▶ Merge Job (coordination)
```

### Vertical Scaling

**Current Limits**:
- 7 GB RAM per runner
- 2 CPU cores
- 6-hour timeout

**Optimizations**:
- Stream processing (no full-memory loads)
- Disk-backed queue (SQLite)
- Bounded caches (LRU eviction)

### Database Scalability

**Current**: SQLite (embedded)
**Future**: PostgreSQL/MySQL for multi-instance

**Migration Path**:
```python
# Abstract database interface
class Store(ABC):
    @abstractmethod
    def save_proxy(self, proxy): ...

class SQLiteStore(Store): ...
class PostgreSQLStore(Store): ...
```

---

## Monitoring & Observability

### Metrics

```python
{
  "pipeline_duration": 1847.5,  # seconds
  "sources_fetched": 668,
  "proxies_parsed": 15234,
  "proxies_tested": 12105,
  "proxies_working": 3842,
  "success_rate": 0.317,
  "average_latency": 287.3,
  "error_rate": 0.08
}
```

### Logging Levels

- **DEBUG**: Detailed execution trace
- **INFO**: Key pipeline events
- **WARNING**: Anomalies, fallbacks
- **ERROR**: Failures, exceptions
- **CRITICAL**: Pipeline termination

### Distributed Tracing

```python
trace_id = generate_trace_id()
logger.info("Fetch source", extra={"trace_id": trace_id})
logger.info("Test proxy", extra={"trace_id": trace_id})
```

---

## Future Improvements

### 1. Real-Time Updates

Replace 6-hour schedule with continuous streaming:

```python
async def continuous_pipeline():
    while True:
        for source in sources:
            if has_new_data(source):
                await process_source(source)
        await asyncio.sleep(60)
```

### 2. Machine Learning

- Predict proxy lifespan
- Anomaly detection (Isolation Forest → LSTM)
- Smart source prioritization

### 3. Distributed Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Fetcher 1  │     │  Fetcher 2  │     │  Fetcher 3  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
                   ┌───────────────┐
                   │  Message Queue│
                   │   (RabbitMQ)  │
                   └───────┬───────┘
                           ▼
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Tester 1   │     │  Tester 2   │     │  Tester 3   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
                   ┌───────────────┐
                   │   PostgreSQL  │
                   └───────────────┘
```

### 4. CDN Integration

- Cloudflare Workers for API
- Edge caching for proxies
- Global distribution

---

## Conclusion

ConfigStream's architecture balances **simplicity**, **performance**, and **reliability**. The producer-consumer pipeline, async/await concurrency, and zero-cost deployment strategy enable processing thousands of proxies every 6 hours with minimal infrastructure.

Key architectural decisions:
- ✅ **Async/Await**: 50× better concurrency than threads
- ✅ **SQLite**: Zero-cost, reliable persistence
- ✅ **GitHub Actions**: Free CI/CD infrastructure
- ✅ **Atomic Writes**: Data integrity guarantees
- ✅ **AIMD Concurrency**: Self-tuning performance
- ✅ **Security-First**: Defense in depth

---

**Last Updated**: 2025-12-23
**Version**: 2.0.12
**Author**: ConfigStream Team
