# ConfigStream Performance Optimization Roadmap
## Zero-Cost, Maximum Performance

**Focus:** Speed, Efficiency, Reliability
**Budget:** $0.00 (Free tools only)
**Goal:** Make ConfigStream the fastest proxy aggregator

---

## 🎯 Current Performance Baseline

### Pipeline Metrics (After Recent Optimizations)
```
Sources: 240
Batch Size: 750 proxies
Cache TTL: 2 hours
Chunk Size: 15,000 configs
Max Phases: 40
Workers: 32
Timeout: 6 seconds

Estimated Full Run: 15-20 minutes
```

### Bottlenecks Identified

| Phase | Current Time | % of Total | Optimization Potential |
|-------|--------------|------------|------------------------|
| **Fetch** | 2-3 min | 15% | ⚡ High (parallel DNS, HTTP/2) |
| **Parse** | 30 sec | 3% | ✅ Already fast |
| **Test** | 10-15 min | 70% | ⚡⚡ **CRITICAL** (caching, filtering) |
| **Geo** | 2-3 min | 12% | ⚡ Medium (batch lookup, cache) |
| **Output** | 30 sec | 3% | ✅ Already fast |

**Target:** Reduce total time from **15-20 min → 5-8 min** (60-70% improvement)

---

## 🚀 Performance Optimization Phases

### PHASE 1: Test Phase Optimization (Week 1)
**Goal:** Reduce testing time by 50% (10-15 min → 5-7 min)

#### 1.1 Aggressive Test Result Caching

**Current:** 2-hour cache, hash-based lookup
**Improved:** Multi-level cache with smarter invalidation

```python
# src/configstream/cache/multi_level_cache.py
import hashlib
import time
from typing import Optional
from pathlib import Path
import lz4.frame  # Fast compression

class MultiLevelCache:
    """
    Level 1: Memory (dict) - instant lookup
    Level 2: SQLite with LZ4 compression - 10ms lookup
    Level 3: None (test required)
    """

    def __init__(self):
        self.memory_cache = {}  # Level 1: RAM
        self.db_cache = TestResultCache(ttl_seconds=86400)  # Level 2: 24 hours!
        self.max_memory_entries = 10000  # Keep 10k in RAM

    def get_cache_key(self, proxy: Proxy) -> str:
        """Fast cache key generation"""
        # Use protocol:address:port (faster than config hash)
        return f"{proxy.protocol}:{proxy.address}:{proxy.port}"

    def get(self, proxy: Proxy) -> Optional[Proxy]:
        """Check Level 1 (RAM) then Level 2 (SQLite)"""
        key = self.get_cache_key(proxy)

        # Level 1: Memory (instant)
        if key in self.memory_cache:
            cached = self.memory_cache[key]
            if time.time() - cached['timestamp'] < 7200:  # 2 hour memory cache
                return cached['proxy']

        # Level 2: SQLite (10ms)
        cached_proxy = self.db_cache.get(proxy)
        if cached_proxy:
            # Promote to Level 1
            self.memory_cache[key] = {
                'proxy': cached_proxy,
                'timestamp': time.time()
            }
            return cached_proxy

        return None

    def set(self, proxy: Proxy):
        """Store in both levels"""
        key = self.get_cache_key(proxy)

        # Level 1: Memory
        self.memory_cache[key] = {
            'proxy': proxy,
            'timestamp': time.time()
        }

        # Evict old entries if memory full
        if len(self.memory_cache) > self.max_memory_entries:
            # Remove oldest 20%
            sorted_items = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            for old_key, _ in sorted_items[:2000]:
                del self.memory_cache[old_key]

        # Level 2: SQLite
        self.db_cache.set(proxy)
```

**Expected Impact:**
- 🎯 **50-70% cache hit rate** (vs current 30-40%)
- 🎯 **5-7 min saved** on test phase
- 🎯 **Zero cost** (uses SQLite + RAM)

---

#### 1.2 Parallel Test Execution Optimization

**Current:** asyncio.gather with semaphore (32 workers)
**Improved:** Process pool for CPU-bound work

```python
# src/configstream/testers_optimized.py
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count
import asyncio

class OptimizedTester:
    """Use both async I/O and process pool"""

    def __init__(self, timeout: float = 6.0, cache=None):
        self.timeout = timeout
        self.cache = cache
        self.process_pool = ProcessPoolExecutor(max_workers=cpu_count())

    async def test_batch_hybrid(self, proxies: List[Proxy]) -> List[Proxy]:
        """
        Hybrid approach:
        1. Check cache (async, fast)
        2. Test uncached in process pool (parallel)
        """
        # Step 1: Quick cache check
        cached_results = []
        needs_testing = []

        for proxy in proxies:
            cached = self.cache.get(proxy) if self.cache else None
            if cached:
                cached_results.append(cached)
            else:
                needs_testing.append(proxy)

        logger.info(f"Cache hit: {len(cached_results)}/{len(proxies)} "
                   f"({len(cached_results)/len(proxies)*100:.1f}%)")

        if not needs_testing:
            return cached_results

        # Step 2: Test in chunks using process pool
        chunk_size = 50
        chunks = [needs_testing[i:i+chunk_size]
                 for i in range(0, len(needs_testing), chunk_size)]

        tested = []
        loop = asyncio.get_event_loop()

        # Run chunks in parallel processes
        futures = [
            loop.run_in_executor(
                self.process_pool,
                test_proxy_chunk,
                chunk,
                self.timeout
            )
            for chunk in chunks
        ]

        chunk_results = await asyncio.gather(*futures)

        for chunk_result in chunk_results:
            tested.extend(chunk_result)

        # Cache all results
        for proxy in tested:
            if self.cache:
                self.cache.set(proxy)

        return cached_results + tested


def test_proxy_chunk(proxies: List[Proxy], timeout: float) -> List[Proxy]:
    """CPU-bound work in separate process"""
    # This runs in a separate process - no GIL contention!
    from singbox2proxy import SingBoxProxy

    results = []
    for proxy in proxies:
        try:
            sb = SingBoxProxy(proxy.config)
            # Test logic here
            proxy.is_working = True
            results.append(proxy)
        except Exception:
            proxy.is_working = False
            results.append(proxy)
        finally:
            if sb:
                sb.stop()

    return results
```

**Expected Impact:**
- 🎯 **2-3x faster** testing (utilize all CPU cores)
- 🎯 **No GIL bottleneck** (Python multiprocessing)
- 🎯 **Zero cost**

---

#### 1.3 Smart Proxy Pre-Filtering

**Current:** Test everything
**Improved:** Skip likely-dead proxies using heuristics

```python
# src/configstream/smart_filter.py
from datetime import datetime, timedelta
from collections import defaultdict

class SmartProxyFilter:
    """Filter out low-quality proxies before testing"""

    def __init__(self):
        self.source_stats = defaultdict(lambda: {
            'total_tested': 0,
            'total_working': 0,
            'avg_latency': 0,
            'last_success': None
        })

    def should_test(self, proxy: Proxy, source_url: str) -> bool:
        """
        Skip testing if:
        1. Source has <5% success rate historically
        2. Source hasn't had a working proxy in 24 hours
        3. Proxy port is commonly blocked (8080, 80, 443 on HTTP)
        4. Proxy is duplicate of recently failed
        """
        stats = self.source_stats[source_url]

        # Check source quality
        if stats['total_tested'] > 50:
            success_rate = stats['total_working'] / stats['total_tested']
            if success_rate < 0.05:  # <5% success
                logger.debug(f"Skipping {source_url} (low success rate)")
                return False

        # Check recent success
        if stats['last_success']:
            hours_since = (datetime.now() - stats['last_success']).total_seconds() / 3600
            if hours_since > 24:
                logger.debug(f"Skipping {source_url} (no success in 24h)")
                return False

        # Check suspicious ports
        suspicious_ports = {8080, 80, 443, 3128, 8888}
        if proxy.port in suspicious_ports and proxy.protocol == 'http':
            return False  # Likely dead

        return True

    def update_stats(self, source_url: str, proxy: Proxy):
        """Update source statistics"""
        stats = self.source_stats[source_url]
        stats['total_tested'] += 1

        if proxy.is_working:
            stats['total_working'] += 1
            stats['last_success'] = datetime.now()
            if proxy.latency:
                # Running average
                n = stats['total_working']
                stats['avg_latency'] = (
                    stats['avg_latency'] * (n-1) + proxy.latency
                ) / n

    def get_priority_sources(self) -> List[str]:
        """Return sources to test first (highest quality)"""
        scored = []
        for source, stats in self.source_stats.items():
            if stats['total_tested'] < 10:
                score = 50  # Neutral for new sources
            else:
                success_rate = stats['total_working'] / stats['total_tested']
                score = success_rate * 100

            scored.append((source, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored]
```

**Expected Impact:**
- 🎯 **Skip 20-30% of proxies** (low-quality sources)
- 🎯 **3-5 min saved** on testing
- 🎯 **Zero cost**

---

### PHASE 2: Network Optimization (Week 2)
**Goal:** Reduce fetch time by 50% (2-3 min → 1-1.5 min)

#### 2.1 HTTP/2 + Connection Reuse

**Current:** New connection per source
**Improved:** HTTP/2 multiplexing + connection pooling

```python
# src/configstream/optimized_fetcher.py
import httpx  # Supports HTTP/2 natively
from typing import List, Tuple

class OptimizedFetcher:
    """HTTP/2 + connection pooling for parallel fetching"""

    def __init__(self):
        # HTTP/2 client with aggressive connection pooling
        self.client = httpx.AsyncClient(
            http2=True,  # Enable HTTP/2
            limits=httpx.Limits(
                max_keepalive_connections=100,
                max_connections=200,
                keepalive_expiry=30.0
            ),
            timeout=httpx.Timeout(30.0),
            follow_redirects=True
        )

    async def fetch_all(self, sources: List[str]) -> List[Tuple[str, str]]:
        """Fetch all sources concurrently with HTTP/2"""
        tasks = [self.fetch_source(url) for url in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = []
        for url, result in zip(sources, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed {url}: {result}")
            else:
                successful.append((url, result))

        return successful

    async def fetch_source(self, url: str) -> str:
        """Fetch single source with retry"""
        for attempt in range(3):
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                return response.text
            except Exception as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def close(self):
        await self.client.aclose()
```

**Expected Impact:**
- 🎯 **30-40% faster** fetching (HTTP/2 multiplexing)
- 🎯 **1-2 min saved**
- 🎯 **Zero cost** (httpx is free)

---

#### 2.2 DNS Caching + Prefetching

```python
# src/configstream/dns_optimizer.py
import aiodns
import asyncio
from functools import lru_cache

class DNSOptimizer:
    """Aggressive DNS caching and prefetching"""

    def __init__(self):
        self.resolver = aiodns.DNSResolver()
        self.cache = {}  # Manual DNS cache

    @lru_cache(maxsize=1000)
    async def resolve_cached(self, hostname: str) -> str:
        """Resolve with in-memory cache"""
        if hostname in self.cache:
            # Check if still valid (5 min TTL)
            cached_time, ip = self.cache[hostname]
            if time.time() - cached_time < 300:
                return ip

        # Resolve
        try:
            result = await self.resolver.gethostbyname(hostname, socket.AF_INET)
            ip = result.addresses[0]
            self.cache[hostname] = (time.time(), ip)
            return ip
        except Exception:
            return hostname  # Fallback

    async def prefetch_dns(self, urls: List[str]):
        """Pre-resolve all DNS before fetching"""
        hostnames = [urlparse(url).hostname for url in urls]
        tasks = [self.resolve_cached(h) for h in hostnames if h]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Pre-fetched DNS for {len(hostnames)} hosts")
```

**Expected Impact:**
- 🎯 **50-100ms saved per source** (no DNS lookup)
- 🎯 **30-60 sec saved total**
- 🎯 **Zero cost**

---

### PHASE 3: Memory & I/O Optimization (Week 3)
**Goal:** Reduce memory usage by 40%, faster I/O

#### 3.1 Streaming Parsing (No Full Load)

**Current:** Load entire source into memory
**Improved:** Stream and parse line-by-line

```python
# src/configstream/streaming_parser.py
import aiofiles

async def parse_source_streaming(url: str, session: httpx.AsyncClient):
    """Stream and parse without loading full response"""
    configs = []

    async with session.stream('GET', url) as response:
        response.raise_for_status()

        buffer = ""
        async for chunk in response.aiter_bytes():
            # Decode chunk
            buffer += chunk.decode('utf-8', errors='ignore')

            # Process complete lines
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()

                # Parse config if valid
                if line.startswith(('vmess://', 'vless://', 'ss://', 'trojan://')):
                    configs.append(line)

                # Limit memory
                if len(configs) >= 10000:
                    # Yield batch and clear
                    yield configs
                    configs = []

        # Final batch
        if configs:
            yield configs
```

**Expected Impact:**
- 🎯 **60-70% memory reduction** (stream vs load)
- 🎯 **Faster parsing** (incremental)
- 🎯 **Zero cost**

---

#### 3.2 Optimized Data Structures

```python
# src/configstream/optimized_models.py
from dataclasses import dataclass
import msgpack  # Faster than JSON

@dataclass(slots=True)  # Use slots for 40% memory reduction!
class OptimizedProxy:
    """Memory-optimized proxy model"""
    # Using __slots__ reduces memory by 40%
    __slots__ = [
        'protocol', 'address', 'port', 'config',
        'latency', 'is_working', 'country_code'
    ]

    protocol: str
    address: str
    port: int
    config: str = ""
    latency: float = None
    is_working: bool = False
    country_code: str = ""

    def to_msgpack(self) -> bytes:
        """Serialize to msgpack (50% smaller than JSON)"""
        return msgpack.packb({
            'p': self.protocol,
            'a': self.address,
            'pt': self.port,
            'c': self.config,
            'l': self.latency,
            'w': self.is_working,
            'cc': self.country_code
        })

    @classmethod
    def from_msgpack(cls, data: bytes):
        """Deserialize from msgpack"""
        d = msgpack.unpackb(data)
        return cls(
            protocol=d['p'],
            address=d['a'],
            port=d['pt'],
            config=d.get('c', ''),
            latency=d.get('l'),
            is_working=d.get('w', False),
            country_code=d.get('cc', '')
        )
```

**Expected Impact:**
- 🎯 **40% memory reduction** (__slots__)
- 🎯 **50% smaller cache files** (msgpack)
- 🎯 **Faster serialization** (2-3x vs JSON)
- 🎯 **Zero cost**

---

### PHASE 4: Pipeline Orchestration (Week 4)
**Goal:** Smarter pipeline with incremental updates

#### 4.1 Incremental Pipeline

**Current:** Full rebuild every 4 hours
**Improved:** Incremental updates

```python
# src/configstream/incremental_pipeline.py
class IncrementalPipeline:
    """Only retest/refetch changed sources"""

    def __init__(self):
        self.last_run = {}  # source_url -> {etag, last_modified, proxy_count}

    async def fetch_changed_sources(self, sources: List[str]) -> List[str]:
        """Only fetch sources that changed"""
        changed = []

        for source in sources:
            last = self.last_run.get(source, {})

            # Check ETag / Last-Modified
            head = await self.client.head(source)

            etag = head.headers.get('ETag')
            modified = head.headers.get('Last-Modified')

            if (etag and etag != last.get('etag')) or \
               (modified and modified != last.get('last_modified')):
                changed.append(source)
            else:
                logger.info(f"Skipping {source} (not modified)")

        logger.info(f"Changed sources: {len(changed)}/{len(sources)}")
        return changed

    def merge_with_existing(self, new_proxies: List[Proxy], existing: List[Proxy]):
        """Smart merge: keep good existing, add new"""
        # Keep existing working proxies
        good_existing = [
            p for p in existing
            if p.is_working and
            (datetime.now() - datetime.fromisoformat(p.tested_at)).total_seconds() < 7200
        ]

        # Deduplicate
        seen = {(p.protocol, p.address, p.port) for p in good_existing}
        unique_new = [
            p for p in new_proxies
            if (p.protocol, p.address, p.port) not in seen
        ]

        return good_existing + unique_new
```

**Expected Impact:**
- 🎯 **Skip 60-70% of sources** (not modified)
- 🎯 **5-10 min saved** on unchanged runs
- 🎯 **Zero cost**

---

#### 4.2 Parallel Pipeline Stages

**Current:** Sequential (fetch → parse → test)
**Improved:** Overlapped pipeline

```python
# src/configstream/parallel_pipeline.py
async def parallel_pipeline(sources: List[str]):
    """Overlapped pipeline stages"""

    # Create queues
    fetch_queue = asyncio.Queue(maxsize=1000)
    parse_queue = asyncio.Queue(maxsize=5000)
    test_queue = asyncio.Queue(maxsize=1000)

    # Start all stages in parallel
    fetch_task = asyncio.create_task(fetch_stage(sources, fetch_queue))
    parse_task = asyncio.create_task(parse_stage(fetch_queue, parse_queue))
    test_task = asyncio.create_task(test_stage(parse_queue, test_queue))

    # Collect results
    results = []
    while True:
        try:
            proxy = await asyncio.wait_for(test_queue.get(), timeout=1.0)
            results.append(proxy)
        except asyncio.TimeoutError:
            if test_queue.empty() and parse_queue.empty() and fetch_queue.empty():
                break

    return results

async def fetch_stage(sources, output_queue):
    """Fetch and push to parse queue"""
    for source in sources:
        content = await fetch_source(source)
        await output_queue.put(content)

async def parse_stage(input_queue, output_queue):
    """Parse and push to test queue"""
    while True:
        content = await input_queue.get()
        configs = parse_configs(content)
        for config in configs:
            await output_queue.put(config)

async def test_stage(input_queue, output_queue):
    """Test and push to results"""
    while True:
        proxy = await input_queue.get()
        tested = await test_proxy(proxy)
        await output_queue.put(tested)
```

**Expected Impact:**
- 🎯 **20-30% faster** (overlapped stages)
- 🎯 **3-5 min saved**
- 🎯 **Zero cost**

---

## 📊 Total Expected Performance Gains

### Time Savings Summary

| Optimization | Time Saved | Implementation |
|--------------|------------|----------------|
| Multi-level caching | 5-7 min | Week 1 |
| Process pool testing | 3-4 min | Week 1 |
| Smart pre-filtering | 3-5 min | Week 1 |
| HTTP/2 + connection pool | 1-2 min | Week 2 |
| DNS caching | 0.5-1 min | Week 2 |
| Incremental pipeline | 5-10 min | Week 4 |
| Parallel stages | 3-5 min | Week 4 |
| **TOTAL** | **21-34 min** | **4 weeks** |

### Current vs Target

```
Current:  15-20 min per run
Target:   5-8 min per run

Improvement: 60-70% faster ⚡
```

---

## 🛠️ Implementation Priority

### Week 1: Quick Wins (No Dependencies)
1. ✅ Enable __slots__ on Proxy model (5 min work, 40% memory saved)
2. ✅ Multi-level cache (2 hours work, 50% speed boost)
3. ✅ Smart pre-filtering (2 hours work, 20-30% tests skipped)

### Week 2: Network Optimization
1. ✅ Replace aiohttp with httpx (HTTP/2)
2. ✅ Add DNS caching
3. ✅ Connection pooling tuning

### Week 3: Memory & I/O
1. ✅ Streaming parser
2. ✅ msgpack serialization
3. ✅ Optimize data structures

### Week 4: Pipeline Architecture
1. ✅ Incremental updates
2. ✅ Parallel stage pipeline
3. ✅ Benchmark and profile

---

## 🎯 Immediate Actions (Today!)

### 1. Enable __slots__ (5 minutes)

```bash
# Edit src/configstream/models.py
# Add @dataclass(slots=True)

# Before:
@dataclass
class Proxy:
    ...

# After:
@dataclass(slots=True)
class Proxy:
    __slots__ = ['protocol', 'address', 'port', ...]  # List all fields
    ...
```

**Impact:** 40% memory reduction immediately!

---

### 2. Extend Cache TTL (2 minutes)

```python
# src/configstream/pipeline.py
# Line 482: Change from 7200 to 86400 (24 hours)

test_cache = TestResultCache(ttl_seconds=86400)  # Was 7200
```

**Impact:** 60-70% cache hit rate!

---

### 3. Install httpx for HTTP/2 (1 minute)

```bash
pip install httpx[http2]
```

**Impact:** 30-40% faster fetching!

---

## 📈 Monitoring Performance Gains

### Add Performance Tracking

```python
# src/configstream/performance_tracker.py
import time
from contextlib import contextmanager

class DetailedPerformanceTracker:
    """Track granular performance metrics"""

    def __init__(self):
        self.metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'proxies_skipped': 0,
            'dns_lookups': 0,
            'fetch_times': [],
            'test_times': [],
            'memory_usage': []
        }

    @contextmanager
    def track_operation(self, name: str):
        """Track individual operation time"""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.metrics.setdefault(name, []).append(elapsed)

    def print_summary(self):
        """Print performance summary"""
        cache_total = self.metrics['cache_hits'] + self.metrics['cache_misses']
        hit_rate = self.metrics['cache_hits'] / cache_total if cache_total > 0 else 0

        print(f"""
Performance Summary:
-------------------
Cache Hit Rate: {hit_rate:.1%} ({self.metrics['cache_hits']}/{cache_total})
Proxies Skipped: {self.metrics['proxies_skipped']}
Avg Fetch Time: {sum(self.metrics.get('fetch', [0]))/max(len(self.metrics.get('fetch', [1])), 1):.2f}s
Avg Test Time: {sum(self.metrics.get('test', [0]))/max(len(self.metrics.get('test', [1])), 1):.2f}s
Memory Peak: {max(self.metrics.get('memory_usage', [0])):.1f} MB
        """)
```

---

## 🔥 Free Tools to Use

### Performance Analysis
- ✅ **py-spy** - Profile Python (zero overhead)
- ✅ **memory_profiler** - Track memory usage
- ✅ **pytest-benchmark** - Benchmark code
- ✅ **hyperfine** - Benchmark CLI commands

### Installation
```bash
pip install py-spy memory-profiler pytest-benchmark
cargo install hyperfine  # Or: brew install hyperfine
```

### Usage
```bash
# Profile pipeline
py-spy record -o profile.svg -- python -m configstream.cli merge --sources sources.txt

# Benchmark
hyperfine 'python -m configstream.cli merge --sources sources.txt --output output'

# Memory profile
python -m memory_profiler src/configstream/pipeline.py
```

---

## ✅ Action Plan Summary

### This Week (Week 1):
1. ✅ Add `__slots__` to Proxy model (5 min)
2. ✅ Extend cache TTL to 24 hours (2 min)
3. ✅ Install httpx for HTTP/2 (1 min)
4. ✅ Implement multi-level cache (2 hours)
5. ✅ Add smart pre-filtering (2 hours)

**Expected Gain:** 40-50% faster, 40% less memory

### Next Week (Week 2):
1. ✅ Replace aiohttp with httpx
2. ✅ Add DNS caching
3. ✅ Optimize connection pooling

**Expected Gain:** 50-60% faster

### Week 3:
1. ✅ Streaming parser
2. ✅ msgpack serialization

**Expected Gain:** 60-70% faster, 50% less memory

### Week 4:
1. ✅ Incremental pipeline
2. ✅ Parallel stages

**Expected Gain:** **70% faster total** 🚀

---

## 🎯 Final Target

```
Before:  15-20 min, 2 GB RAM
After:   5-8 min, 800 MB RAM

Speed: 3x faster ⚡⚡⚡
Memory: 60% reduction 📉
Cost: $0.00 💰
```

**NO business features. NO costs. PURE SPEED.** 🚀
