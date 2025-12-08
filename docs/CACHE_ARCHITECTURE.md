# ConfigStream Cache Architecture

**Version:** 2.0
**Last Updated:** December 2025

## Overview

ConfigStream implements a sophisticated **context-aware caching system** that optimizes performance while ensuring data freshness. The system automatically detects when data has been updated (via pipeline runs or retest operations) and invalidates cache only when necessary.

## Architecture Components

### 1. **Smart Update Detection**

#### UpdateDetector (`frontend/assets/js/update-detector.js`)

The `UpdateDetector` is the core of context-aware caching. It:

- **Polls every 4 minutes** for data updates
- **Detects actual changes** by comparing timestamps
- **Triggers selective fetches** only for updated resources
- **Persists state** across browser sessions via localStorage

**Key Features:**
```javascript
// Lightweight polling
checkForUpdates() // Uses HTTP HEAD or minimal JSON parsing

// Smart timestamp comparison
processTimestamps() // Detects only real changes

// Selective resource fetching
fetchUpdatedResources(['metadata', 'proxies']) // Only fetches what changed

// Event-driven updates
window.dispatchEvent('configstream:dataUpdated') // Notifies components
```

**Benefits:**
- ✅ No dependency on GitHub Actions schedules
- ✅ Real-time update detection
- ✅ Minimal network usage (lightweight polling)
- ✅ Automatic cache invalidation

### 2. **Multi-Layer Caching Strategy**

#### Cache Configuration (`frontend/assets/js/cache-config.js`)

ConfigStream uses three caching strategies:

| Strategy | Use Case | Resources |
|----------|----------|-----------|
| **networkOnly** | Never cache (reserved) | None currently |
| **networkFirst** | Dynamic data | `metadata.json`, `proxies.json`, `statistics.json` |
| **cacheFirst** | Static assets | CSS, JS, images, fonts |

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

### 3. **Automatic Cache Invalidation**

#### Version-Based Invalidation

On every deployment, the cache version is automatically updated:

```bash
# From .github/workflows/deploy-pages.yml
ts=$(date +%Y%m%d%H%M%S)
sed -i "s/const VERSION = '[^']*'/const VERSION = '${ts}'/" cache-config.js
```

**Effect:**
- Cache name changes: `configstream-v20251208120000`
- Old caches automatically purged by service worker
- All users get fresh assets on next visit

#### Timestamp-Based Invalidation

UpdateDetector compares `last_updated_utc` timestamps:

```javascript
// Old timestamp from localStorage
lastKnownTimestamps['metadata'] = "2025-12-08T11:30:00Z"

// New timestamp from server
currentTimestamp = "2025-12-08T12:00:00Z"

// Update detected → fetch fresh data
if (new Date(currentTimestamp) > new Date(lastKnownTimestamps['metadata'])) {
    fetchUpdatedResources(['metadata']);
}
```

### 4. **Stale-While-Revalidate Pattern**

**How it works:**
1. User requests `metadata.json`
2. Serve cached version immediately (fast response)
3. Fetch fresh version in background
4. Update cache for next request

**Benefits:**
- ⚡ Instant page loads (cached data)
- 🔄 Always fresh data (background updates)
- 📱 Works offline (cached fallback)

## Data Flow

### Initial Page Load

```
User visits page
    ↓
1. Load cached assets (cacheFirst)
    ↓
2. Fetch metadata.json (networkFirst)
    ↓
3. Check if timestamp changed
    ↓
4. If changed → invalidate cache
    ↓
5. Fetch fresh data
    ↓
6. Update UI
    ↓
7. Start 4-minute polling
```

### Background Polling (Every 4 minutes)

```
UpdateDetector poll
    ↓
1. Fetch metadata.json (HEAD request or minimal JSON)
    ↓
2. Extract last_updated_utc timestamp
    ↓
3. Compare with last known timestamp
    ↓
4. If changed:
   - Fetch full data for changed resources
   - Invalidate cache entries
   - Trigger callbacks
   - Dispatch 'configstream:dataUpdated' event
   - Update localStorage
    ↓
5. If unchanged:
   - Do nothing (no unnecessary fetches)
```

### Pipeline/Retest Trigger

```
GitHub Actions pipeline runs
    ↓
1. Generate new proxies.json, metadata.json
    ↓
2. Update last_updated_utc timestamp
    ↓
3. Deploy to GitHub Pages
    ↓
4. Update VERSION in cache-config.js
    ↓
5. Users' UpdateDetector polls
    ↓
6. Detects timestamp change
    ↓
7. Fetches fresh data automatically
    ↓
8. UI updates in real-time
```

## Cache Lifecycle

### Resource Types

#### 1. Dynamic Data (Updated by Pipeline/Retest)
- **metadata.json** - Proxy counts, last_updated timestamps, sources
- **proxies.json** - Full proxy list
- **statistics.json** - Aggregated stats

**Cache Strategy:**
- networkFirst with 5-10 minute expiry
- UpdateDetector polls every 4 minutes
- Timestamp-based invalidation

#### 2. Static Assets (Versioned by Deployment)
- **CSS files** - Stylesheets
- **JS files** - Scripts
- **Fonts** - Typography
- **Images** - Icons, backgrounds

**Cache Strategy:**
- cacheFirst with version-based invalidation
- Update only on deployment (VERSION change)

#### 3. Hybrid Resources
- **HTML pages** - networkFirst (always fresh navigation)
- **Service Worker** - Auto-update mechanism

## Performance Optimizations

### 1. Minimal Network Usage

**Before (Naive Approach):**
- Fetch all data every load = ~2MB every visit
- No caching = slow page loads
- Relies on GitHub Actions schedule

**After (Smart Caching):**
- Serve cached data = instant load
- Poll lightweight status = <1KB every 4 minutes
- Fetch only changed resources = selective updates

**Savings:** ~99% reduction in unnecessary network requests

### 2. localStorage Persistence

```javascript
// Persist timestamps across sessions
localStorage.setItem('configstream_last_timestamps', JSON.stringify({
    metadata: "2025-12-08T12:00:00Z",
    proxies: "2025-12-08T12:00:00Z",
    statistics: "2025-12-08T12:00:00Z"
}));
```

**Benefits:**
- No unnecessary fetches on page reload
- Faster initial load
- State preserved across sessions

### 3. Background Updates

```javascript
// User sees instant UI (cached data)
displayData(cachedMetadata);

// Fresh data fetches in background
fetch('metadata.json').then(fresh => {
    if (fresh.last_updated !== cachedMetadata.last_updated) {
        updateUI(fresh);
        updateCache(fresh);
    }
});
```

## Event System

### Global Events

Components can listen for data updates:

```javascript
// Register callback for metadata updates
window.updateDetector.onUpdate('metadata', (data) => {
    console.log('Metadata updated:', data);
    updateUI(data);
});

// Listen for global update event
window.addEventListener('configstream:dataUpdated', (e) => {
    console.log('Resources updated:', e.detail.resources);
    // ['metadata', 'proxies']
});
```

### Page Visibility Integration

```javascript
// Pause polling when tab is hidden (save resources)
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        updateDetector.stopPolling();
    } else {
        updateDetector.startPolling();
    }
});
```

## Deployment Integration

### GitHub Actions Workflow

The deployment workflow automatically:

1. **Builds frontend** with latest data
2. **Updates cache version** with timestamp
3. **Deploys to GitHub Pages**
4. **Updates metadata timestamps**

```yaml
# .github/workflows/deploy-pages.yml
- name: Update cache version
  run: |
    ts=$(date +%Y%m%d%H%M%S)
    sed -i "s/const VERSION = '[^']*'/const VERSION = '${ts}'/" \
      output/assets/js/cache-config.js
```

### Service Worker

The service worker:
- Pre-caches critical assets
- Purges old cache versions
- Implements caching strategies
- Handles offline mode

```javascript
// Auto-delete old caches
const cacheWhitelist = [`configstream-v${VERSION}`];
caches.keys().then(cacheNames => {
    return Promise.all(
        cacheNames.map(cacheName => {
            if (!cacheWhitelist.includes(cacheName)) {
                return caches.delete(cacheName);
            }
        })
    );
});
```

## Monitoring & Debugging

### Console Logs

UpdateDetector provides detailed logging:

```
[UpdateDetector] Starting polling (interval: 4 minutes)
[UpdateDetector] Polling for updates...
[UpdateDetector] Update detected for metadata: {old: "...", new: "..."}
[UpdateDetector] Updates found: ["metadata", "proxies"]
```

### Manual Control

Debug utilities exposed globally:

```javascript
// Force immediate update check
window.updateDetector.forceCheck();

// View last known timestamps
console.log(window.updateDetector.lastKnownTimestamps);

// Stop/start polling
window.updateDetector.stopPolling();
window.updateDetector.startPolling();
```

## Best Practices

### For Developers

1. **Never hardcode URLs** - Use `window.getFullUrl()`
2. **Register update callbacks** - React to data changes
3. **Use stale-while-revalidate** - Best UX
4. **Increment VERSION** - Force cache refresh when needed
5. **Update timestamps** - Ensure last_updated_utc is current

### For Users

1. **Allow background updates** - Keep tab open for polling
2. **Hard refresh if needed** - Ctrl+F5 to bypass cache
3. **Check last updated** - Footer shows timestamp

## Troubleshooting

### Issue: Data not updating

**Check:**
1. Is timestamp in metadata.json current?
2. Is UpdateDetector running? (Check console)
3. Is localStorage full? (Clear if needed)
4. Hard refresh (Ctrl+F5)

### Issue: Cache too aggressive

**Solution:**
1. Increment VERSION in cache-config.js
2. Or manually clear: `window.cacheManager.clearAll()`

### Issue: Too many network requests

**Check:**
1. Is polling interval too short? (Should be 4 min)
2. Are multiple tabs open? (Each polls independently)
3. Is service worker registered? (Check dev tools)

## Future Enhancements

- [ ] WebSocket support for instant updates
- [ ] Differential updates (only changed data)
- [ ] Compression for cached data
- [ ] Cache size limits and LRU eviction
- [ ] Analytics on cache hit/miss rates

## Conclusion

ConfigStream's cache architecture provides:

✅ **Performance** - Instant page loads with cached data
✅ **Freshness** - Context-aware updates when data changes
✅ **Reliability** - Offline support with fallback
✅ **Efficiency** - Minimal network usage
✅ **Transparency** - Clear logging and debugging tools

The system automatically adapts to pipeline runs and retest operations without manual intervention or reliance on GitHub Actions schedules.
