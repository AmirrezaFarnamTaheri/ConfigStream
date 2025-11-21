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
│  │  (SQLite-backed, bounded size, backpressure control)      │  │
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
│  │              │   SING-BOX ENGINE   │                       │ │
│  │              │  (Proxy Testing)    │                       │ │
│  │              └─────────────────────┘                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                        │         │
│  ┌────────────────────────────────────────────────────▼──────┐  │
│  │                    POST-PROCESSING                         │  │
│  │  • GeoIP Enrichment   • Scoring   • Filtering             │  │
│  └────────────────────────────────────────────────────┬──────┘  │
│                                                        │         │
│  ┌────────────────────────────────────────────────────▼──────┐  │
│  │                   OUTPUT GENERATION                        │  │
│  │  • Base64  • Clash  • Sing-box  • Shadowrocket  • More    │  │
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
- ETag/Last-Modified caching
- Rate limiting protection
- Hedged requests for critical sources
- Circuit breaker pattern

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

**Supported Protocols** (25+):
- VMess, VLESS, Shadowsocks, Trojan, Hysteria 2
- TUIC, Wireguard, Juicity, SSH, SOCKS5, HTTP
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
    """
```

**Key Functions**:
- **Protocol Detection**: Regex + magic bytes
- **Base64 Decoding**: Handles various padding
- **JSON Parsing**: Nested config structures
- **URI Parsing**: Query string extraction
- **Validation**: Port ranges, cipher support

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

### 4. Tester (`testers.py`)

**Responsibility**: Test proxy functionality

**Test Flow**:
1. **DNS Resolution**: Pre-resolve domains
2. **Connectivity Test**: 3× HTTP requests to test URLs
3. **Latency Measurement**: Median of 3 samples
4. **Security Tests** (if enabled):
   - HTML injection detection
   - Header preservation check
   - SSL certificate validation
   - Honeypot detection

**Implementation**:
```python
class SingBoxTester:
    async def test(self, proxy: Proxy) -> Proxy:
        """
        1. Start sing-box server with proxy config
        2. Connect through SOCKS5 proxy
        3. Perform HTTP requests
        4. Calculate latency
        5. Run security checks
        6. Stop sing-box server
        """
```

**Key Features**:
- **Process Isolation**: Each proxy gets separate sing-box instance
- **Timeout Management**: Per-test and global timeouts
- **Resource Cleanup**: Guaranteed process termination
- **Jitter Calculation**: Stability scoring

---

### 5. GeoIP Resolver (`geoip.py`)

**Responsibility**: Enrich proxies with geographic data

**Data Sources**:
- MaxMind GeoLite2 City (offline)
- MaxMind GeoLite2 ASN (offline)

**Implementation**:
```python
def lookup(ip: str) -> GeoData:
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

### 6. Scorer (`score.py`)

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

3. **Privacy Score**
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

### 7. Output Generator (`output.py`)

**Responsibility**: Generate subscription files

**Output Formats**:
- Base64 subscription URLs
- Clash YAML
- Sing-box JSON
- Surge conf
- Quantumult X
- Shadowrocket
- SIP008 JSON

**Key Features**:
- **Atomic Writes**: Temp file + rename
- **Compression**: Gzipped variants
- **Metadata**: JSON with statistics
- **Country Splits**: Separate files per country

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
      │  SORT by Score      │
      └─────────┬───────────┘
                │
                ▼
      ┌─────────────────────┐
      │  SELECT TOP N       │
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

**Benefits**:
- Adapts to network conditions
- Prevents overwhelming sources
- Maintains stability under load

### Semaphore-Based Limiting

```python
async with concurrency.get_semaphore():
    # Only N concurrent operations allowed
    result = await test_proxy(proxy)
```

### Thread Safety

All shared data structures use async locks:

```python
async with self._stats_lock:
    self.latencies.append(latency)
    self.errors.append(not success)
```

---

## Data Storage

### SQLite Databases

**1. Main Database** (`data/configstream.db`)
- Proxy test results cache
- Source quality history
- Anomaly detection baseline

**2. Queue Database** (`data/queue.db`)
- Persistent work queue
- Survives process crashes

**3. Cache Database** (`data/cache.db`)
- ETag cache for HTTP fetches
- DNS resolution cache

### Schema Examples

```sql
-- Proxy Cache
CREATE TABLE proxy_cache (
    id TEXT PRIMARY KEY,
    config TEXT,
    is_working BOOLEAN,
    latency REAL,
    tested_at TIMESTAMP,
    expires_at TIMESTAMP
);

-- Source Quality
CREATE TABLE source_quality (
    source TEXT PRIMARY KEY,
    fetch_count INTEGER,
    success_count INTEGER,
    average_count REAL,
    diversity_score REAL,
    last_fetch TIMESTAMP
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
│  │  Job: Process (Matrix: batch 1-6)                 │  │
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

**Solution**: Matrix strategy (6 parallel jobs)

```yaml
strategy:
  matrix:
    batch: [1, 2, 3, 4, 5, 6]
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

### 6. Memory Slots

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

**Last Updated**: 2025-11-21
**Version**: 1.3.0
**Author**: ConfigStream Team
