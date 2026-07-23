# SERVER CONCURRENT CACHE AUDIT

## 1. Server Caching Flowchart

```ascii
      Client Request
            |
            v
    [ Route Handler ] (e.g. /api/stats)
            |
            v
 [ _read_json_file_async(path) ]
            |
            +-> Get mtime via asyncio.to_thread(os.path.getmtime)
            |
            +-> Cache Hit? (mtime == cached_mtime)
            |       |
            |       +-- YES --> Return cached JSON payload
            |       |
            |       +-- NO (Cache Miss / Stale)
            |               |
            |               v
            |       [ await asyncio.to_thread(_read_json_file) ] <--- Vulnerable to Cache Stampede
            |               |
            |               v
            |       [ Update _json_cache ]
            |               |
            v               v
  [ JSONResponse ] or [ FileResponse ]
            |
            v
      Client Response
```

## 2. Cache Hit & Invalidation Compliance Table

| Component | Behavior | Compliance Status | Finding |
| :--- | :--- | :--- | :--- |
| **Cache Hit Logic** | Compares `os.path.getmtime` with cached mtime. | ✅ Compliant | Invalidation is tightly coupled to filesystem updates, ensuring freshness. |
| **Concurrency Safety** | Uses `asyncio.to_thread` for IO, but lacks synchronization around cache population. | ❌ Non-Compliant | **Cache Stampede (Thundering Herd)**: Multiple concurrent requests during a cache miss will spawn multiple thread-pool operations to read and parse the same JSON file simultaneously. |
| **File Deletion** | Handles `FileNotFoundError` and removes key from cache. | ✅ Compliant | No `await` between `in` check and `del`, so it is safe from `KeyError` in asyncio's cooperative multitasking. |

## 3. HTTP Caching Headers & ETag Audit

| Endpoint / Method | ETag Present? | Last-Modified Present? | Cache-Control Present? | Finding |
| :--- | :--- | :--- | :--- | :--- |
| `FileResponse` routes | ✅ Yes | ✅ Yes | ❌ No | Starlette automatically adds `ETag` and `Last-Modified`, but lacks explicit `Cache-Control` directives (e.g., `no-cache` or `max-age`), leading to unpredictable client/proxy heuristic caching. |
| `/api/stats` | ❌ No | ❌ No | ❌ No | Uses `JSONResponse` with manually cached data, completely bypassing Starlette's `FileResponse` header generation. This forces clients to re-download the JSON body every time even if it hasn't changed. |

## 4. Memory Allocation & Thread Safety Assessment

- **Thread Safety**: The shared `_json_cache` dictionary is modified in the main asyncio event loop thread. Because dictionary operations are atomic in Python and there are no `await` statements between checking and mutating the dictionary state (outside of the missing stampede lock), there are no race conditions that would corrupt the dictionary itself.
- **Memory Bounds**: `_json_cache` is a simple, unbounded `dict`. While the number of legitimate files is bounded (e.g., `ROOT_OUTPUT_FILES`, country lists), an attacker could theoretically exhaust memory if they found a way to query arbitrary paths that resolve to large JSON files, or if the number of generated country/protocol files grows excessively. An LRU mechanism or TTL bounds should be enforced.

## 5. Hardening Patches

### Patch 1: Mitigate Cache Stampede (Thundering Herd)
Introduce an `asyncio.Lock` per file path to ensure only one coroutine reads and parses the file, while others await the result.

```python
from collections import defaultdict
import asyncio

_json_cache: dict[Path, tuple[float, Any]] = {}
_cache_locks: dict[Path, asyncio.Lock] = defaultdict(asyncio.Lock)

async def _read_json_file_async(path: Path) -> Any:
    try:
        current_mtime = await asyncio.to_thread(os.path.getmtime, path)
    except FileNotFoundError:
        _json_cache.pop(path, None)
        raise

    cached = _json_cache.get(path)
    if cached and cached[0] == current_mtime:
        return cached[1]

    async with _cache_locks[path]:
        # Re-check inside the lock to prevent stampede
        cached = _json_cache.get(path)
        if cached and cached[0] == current_mtime:
            return cached[1]
            
        data = await asyncio.to_thread(_read_json_file, path)
        _json_cache[path] = (current_mtime, data)
        return data
```

### Patch 2: Fix HTTP Caching Headers for `/api/stats`
Generate proper `ETag` and `Cache-Control` headers when returning the `JSONResponse`.

```python
import hashlib

@router.get("/api/stats")
async def get_stats(request: Request):
    metadata_path = OUTPUT_DIR / "metadata.json"
    if not metadata_path.exists():
        return JSONResponse({"status": "initializing"})

    try:
        content = await _read_json_file_async(metadata_path)
        
        # Create an ETag based on the content hash
        content_bytes = json.dumps(content, sort_keys=True).encode("utf-8")
        etag = f'W/"{hashlib.md5(content_bytes).hexdigest()}"'
        
        # Handle If-None-Match
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304)
            
        return JSONResponse(
            content=content, 
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=60"
            }
        )
    except Exception as e:
        logger.error(f"Failed to read metadata.json: {e}")
        return FileResponse(metadata_path)
```

### Patch 3: Enforce Memory Bounds on `_json_cache`
Replace the unbounded dictionary with an LRU Cache to prevent uncontrolled memory growth.

```python
from functools import lru_cache
from cachetools import LRUCache

# Bound the cache to the most recently accessed 128 files
_json_cache = LRUCache(maxsize=128)
```
