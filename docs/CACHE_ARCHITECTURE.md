# ConfigStream Cache Architecture

**Version:** 2.0.5
**Last Updated:** December 2025

## Overview

ConfigStream implements a sophisticated **context-aware caching system** that optimizes performance while ensuring data freshness. The system automatically detects when data has been updated (via pipeline runs or retest operations) and invalidates cache only when necessary. It leverages **IndexedDB** for large datasets and follows a **Stale-While-Revalidate** pattern.

## Architecture Components

### 1. **Smart Update Detection**

#### UpdateDetector (`frontend/assets/js/update-detector.js`)

The `UpdateDetector` is the core of context-aware caching. It:

- **Polls every 4 minutes** for data updates using HTTP `HEAD` requests.
- **Detects actual changes** by comparing `Last-Modified` headers or `last_updated_utc` timestamps.
- **Triggers selective fetches** only for updated resources.
- **Persists state** across browser sessions via localStorage.
- **Resets cache on version mismatch** to ensure major updates are propagated.

**Key Features:**
```javascript
// Lightweight polling
checkForUpdates() // Uses HTTP HEAD or minimal JSON parsing

// Smart timestamp comparison
processTimestamps() // Detects only real changes

// Selective resource fetching
fetchUpdatedResources(['metadata', 'proxies']) // Only fetches what changed

// Version check
checkVersionAndReset() // Clears cache if VERSION changes in cache-config.js
```

### 2. **Multi-Layer Caching Strategy**

#### Cache Configuration (`frontend/assets/js/cache-config.js`)

ConfigStream uses three caching strategies:

| Strategy | Use Case | Resources |
|----------|----------|-----------|
| **networkOnly** | Never cache | None currently |
| **networkFirst** | Dynamic data | `metadata.json`, `proxies.json`, `statistics.json`, `vpn_subscription_base64.txt` |
| **cacheFirst** | Static assets | CSS, JS, images, fonts, HTML pages |

**Configuration:**
```javascript
CACHE_CONFIG: {
  updateStatusExpiry: 4 * 60 * 1000,    // 4 minutes
  metadataExpiry: 5 * 60 * 1000,        // 5 minutes
  proxiesExpiry: 10 * 60 * 1000,        // 10 minutes
  statsExpiry: 5 * 60 * 1000,           // 5 minutes
  networkTimeout: 5000,                 // 5 seconds
  staleWhileRevalidate: true,           // Background updates
  smartUpdateDetection: true            // UpdateDetector enabled
}
```

### 3. **IndexedDB Storage**

#### CacheManager (`frontend/assets/js/cache-manager.js`)

Large datasets (like the full proxy list) are stored in **IndexedDB** to avoid LocalStorage quota limits and blocking the main thread.

- **DB Name:** `ConfigStreamDB`
- **Store:** `apiCache`
- **Helper:** `IDBHelper` class wraps IndexedDB operations with Promises.

### 4. **Service Worker**

#### `frontend/service-worker.js`

The service worker handles offline capabilities and static asset caching.

- **Dynamic Versioning:** Imports version from `cache-config.js`.
- **Pre-caching:** Caches critical assets (`index.html`, `style.css`, `main.js`, etc.) on install.
- **Runtime Caching:** Intercepts requests and applies strategies (Network First vs Cache First).
- **Cleanup:** Automatically deletes old caches on activation.

## Data Flow

### Initial Page Load

```
User visits page
    ↓
1. Service Worker intercepts request (Cache First for HTML/Assets)
    ↓
2. Page loads, scripts initialize
    ↓
3. CacheManager checks IndexedDB/LocalStorage for data
    ↓
4. If cached & fresh → Render UI immediately
    ↓
5. If stale → Render cached, then fetch fresh in background (Stale-While-Revalidate)
    ↓
6. UpdateDetector starts polling (every 4 min)
```

### Background Polling

```
UpdateDetector poll
    ↓
1. HEAD request to metadata.json
    ↓
2. Compare Last-Modified header
    ↓
3. If changed:
   - Fetch full metadata.json
   - Compare specific resource timestamps
   - Fetch only updated resources (e.g. proxies.json)
   - Update IndexedDB
   - Dispatch 'configstream:dataUpdated' event
   - Update UI
```

## Troubleshooting

### Issue: Data not updating

**Check:**
1. Is `metadata.json` timestamp current on the server?
2. Is UpdateDetector running? (Check console logs)
3. Hard refresh (Ctrl+F5) to bypass Service Worker temporarily.

### Issue: Cache too aggressive

**Solution:**
1. Increment `VERSION` in `frontend/assets/js/cache-config.js`.
2. This forces Service Worker update and `UpdateDetector` resets timestamps.

## Future Enhancements

- [ ] WebSocket support for instant push updates.
- [ ] Differential updates (delta patches) for large JSON files.
- [ ] Compression (Brotli/Gzip) for cached data in IndexedDB.
