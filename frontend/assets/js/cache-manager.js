/**
 * Cache Manager for ConfigStream
 * Manages cache expiry, stale-while-revalidate, and data freshness
 * Uses IndexedDB for robust client-side storage of large datasets.
 * Includes Compression (via pako or CompressionStream) support.
 */

// Step 1: Verify that cache configuration is available with graceful fallback
if (!globalThis.ConfigStreamCache) {
  console.warn('[CacheManager] WARNING: Cache configuration not loaded, using defaults');
  // Provide default configuration instead of throwing error
  globalThis.ConfigStreamCache = {
    VERSION: 'v1.0.0-fallback',
    CACHE_NAME: 'configstream-cache-v1',
    CACHE_STRATEGY: 'stale-while-revalidate',
    CACHE_CONFIG: {
      staleWhileRevalidate: true,
      networkTimeout: 5000,
      metadataExpiry: 2 * 60 * 1000,      // 2 minutes
      proxiesExpiry: 10 * 60 * 1000,      // 10 minutes
      statsExpiry: 5 * 60 * 1000,         // 5 minutes
      defaultExpiry: 5 * 60 * 1000        // 5 minutes
    }
  };
}

// Step 2: Get configuration from the shared namespace
const managerConfig = globalThis.ConfigStreamCache;

// --- Compression Helper ---
const Compression = {
    // Check if CompressionStream API is available (modern browsers)
    hasNative: typeof CompressionStream !== 'undefined',
    // Check if pako is loaded (fallback)
    hasPako: typeof pako !== 'undefined',

    async compress(data) {
        // Performance guard: Don't block main thread for huge files
        // Estimation: 1 char ~= 1 byte.
        const jsonStr = JSON.stringify(data);
        if (jsonStr.length > 3 * 1024 * 1024) { // 3MB limit for main thread compression
            return data; // Return raw data (store uncompressed)
        }
        const encoder = new TextEncoder();
        const input = encoder.encode(jsonStr);

        if (this.hasNative) {
            const stream = new ReadableStream({
                start(controller) {
                    controller.enqueue(input);
                    controller.close();
                }
            }).pipeThrough(new CompressionStream('gzip'));
            const response = new Response(stream);
            const blob = await response.blob();
            return await blob.arrayBuffer();
        } else if (this.hasPako) {
            return pako.gzip(input);
        } else {
            // Fallback: No compression, return original string (or object)
            return data;
        }
    },

    async decompress(compressedData) {
        // If data is not ArrayBuffer/Uint8Array, assume it's uncompressed
        if (!(compressedData instanceof ArrayBuffer) && !(compressedData instanceof Uint8Array)) {
            return compressedData;
        }

        let outputStr;
        if (this.hasNative) {
            const stream = new ReadableStream({
                start(controller) {
                    controller.enqueue(compressedData);
                    controller.close();
                }
            }).pipeThrough(new DecompressionStream('gzip'));
            const response = new Response(stream);
            outputStr = await response.text();
        } else if (this.hasPako) {
            outputStr = pako.ungzip(compressedData, { to: 'string' });
        } else {
            throw new Error('No decompression method available');
        }
        return JSON.parse(outputStr);
    }
};

// Step 3: IndexedDB Helper Class
class IDBHelper {
  constructor(dbName, storeName) {
    this.dbName = dbName;
    this.storeName = storeName;
    this.db = null;
    this.log = this.createLogger();
  }

  createLogger() {
    return {
      info: (msg) => { if (location.hostname === 'localhost') console.log(`[IDBHelper] ${msg}`) },
      warn: (msg) => console.warn(`[IDBHelper] ${msg}`),
      error: (msg) => console.error(`[IDBHelper] ${msg}`),
    };
  }

  async openDB() {
    return new Promise((resolve, reject) => {
      if (this.db) {
        resolve(this.db);
        return;
      }
      const request = indexedDB.open(this.dbName, 1);
      request.onerror = () => reject('Error opening IndexedDB');
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };
      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName);
        }
      };
    });
  }

  async get(key) {
    const db = await this.openDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.get(key);
      request.onerror = () => reject('Error getting data from IndexedDB');
      request.onsuccess = () => resolve(request.result);
    });
  }

  async set(key, value) {
    const db = await this.openDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.put(value, key);
      request.onerror = () => reject('Error setting data in IndexedDB');
      request.onsuccess = () => resolve();
    });
  }

  async clear() {
    const db = await this.openDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.clear();
      request.onerror = () => reject('Error clearing IndexedDB store');
      request.onsuccess = () => resolve();
    });
  }
}

// Step 4: Initialize the cache manager
class CacheManager {
  constructor() {
    this.cacheName = managerConfig.CACHE_NAME;
    this.config = managerConfig.CACHE_CONFIG;
    this.strategy = managerConfig.CACHE_STRATEGY;
    this.log = this.createLogger();
    this.initialized = false;
    this._cacheAvailable = undefined;
    this.idb = new IDBHelper('ConfigStreamDB', 'apiCache');
  }

  createLogger() {
    // [AUDIT] Use production-safe logger wrapper
    return {
      info: (msg) => {
          if (window.ConfigStreamLogger) window.ConfigStreamLogger.info(`[CacheManager] ${msg}`);
      },
      warn: (msg) => {
          if (window.ConfigStreamLogger) window.ConfigStreamLogger.warn(`[CacheManager] ${msg}`);
      },
      error: (msg) => {
          if (window.ConfigStreamLogger) window.ConfigStreamLogger.error(`[CacheManager] ${msg}`);
      }
    };
  }

  async init() {
    if (this.initialized) return;

    try {
      if ('serviceWorker' in navigator) {
        // Correctly point to service-worker.js
        const swUrl = new URL('service-worker.js', document.baseURI).toString();

        const scopeUrl = new URL('.', document.baseURI).toString();
        this.swRegistration = await navigator.serviceWorker.register(swUrl, { scope: scopeUrl });
        this.log.info('Service Worker registered successfully');
        this.swRegistration.addEventListener('updatefound', () => this.handleSWUpdate());
        this.startUpdateCheck();
      }
      this.initialized = true;
    } catch (error) {
      this.log.error(`Failed to initialize: ${error.message}`);
    }
  }

  handleSWUpdate() {
      this.log.info('Service Worker update found');
      const newWorker = this.swRegistration.installing;
      newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              this.log.info('New Service Worker installed, ready to activate');
              this.notifyUpdate();
          }
      });
  }

  startUpdateCheck() {
    setInterval(() => {
      this.swRegistration?.update().catch(err => this.log.warn(`Update check failed: ${err.message}`));
    }, 5 * 60 * 1000);
  }

  notifyUpdate() {
    window.dispatchEvent(new CustomEvent('sw-update-ready'));
  }

  async fetchWithCache(url, options = {}) {
    if (options.bypassCache) return this.fetchFresh(url);

    try {
      const cachedData = await this.getCachedData(url);
      const expiryMs = options.expiry ?? cachedData?.expiry ?? this.getExpiryForUrl(url);

      if (cachedData && !this.isExpired(cachedData, expiryMs)) {
        this.log.info(`Using cached data for ${url}`);

        // Differential update check logic stub
        if (options.differentialUpdate && cachedData.version) {
             // Logic: Check HEAD or version file, if newer, fetch diff or fresh
             // For now, we rely on stale-while-revalidate for simpler updates
        }

        if (this.config.staleWhileRevalidate && this.isStale(cachedData, expiryMs)) {
          this.log.info(`Revalidating in background: ${url}`);
          this.fetchFresh(url).catch(err => this.log.warn(`Background revalidation failed: ${err.message}`));
        }
        return cachedData.data;
      }
      return this.fetchFresh(url);
    } catch (error) {
      this.log.error(`fetchWithCache failed for ${url}: ${error.message}`);
      throw error;
    }
  }

  async fetchFresh(url) {
    this.log.info(`Fetching fresh data: ${url}`);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.networkTimeout || 5000);

    try {
      const response = await fetch(url, { signal: controller.signal, headers: { 'Cache-Control': 'no-cache' } });
      clearTimeout(timeoutId);
      if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      const data = await response.json();
      await this.cacheData(url, data);
      return data;
    } catch (error) {
      clearTimeout(timeoutId);
      this.log.error(`fetchFresh failed for ${url}: ${error.message}`);
      throw error;
    }
  }

  async getCachedData(url) {
    if (!this.cacheAvailable) return null;
    try {
      const cacheKey = this.getCacheKey(url);
      const cachedItem = await this.idb.get(cacheKey);

      if (!cachedItem) return null;

      // Decompress if needed
      let rawData = cachedItem.data;
      if (cachedItem.compressed) {
          try {
              rawData = await Compression.decompress(cachedItem.data);
          } catch(e) {
              this.log.error(`Decompression failed for ${url}: ${e}`);
              return null;
          }
      }

      return { data: rawData, timestamp: cachedItem.timestamp, expiry: cachedItem.expiry, version: cachedItem.version };
    } catch (error) {
      this.log.error(`Failed to get cached data for ${url}: ${error.message}`);
      return null;
    }
  }

  async cacheData(url, data) {
    if (!this.cacheAvailable) return false;
    try {
      const cacheKey = this.getCacheKey(url);

      // Compress
      let storedData = data;
      let isCompressed = false;
      try {
          // Only compress large objects (>10KB approx)
          if (JSON.stringify(data).length > 10240) {
              storedData = await Compression.compress(data);
              isCompressed = true;
          }
      } catch(e) {
          this.log.warn(`Compression skipped for ${url}: ${e}`);
      }

      // Store version from data if available (for differential updates)
      const version = data.version || data.last_updated_utc || Date.now();

      const cacheItem = {
          data: storedData,
          compressed: isCompressed,
          timestamp: Date.now(),
          expiry: this.getExpiryForUrl(url),
          version: version
      };

      await this.idb.set(cacheKey, cacheItem);
      return true;
    } catch (error) {
      this.log.error(`Failed to cache data for ${url}: ${error.message}`);
      return false;
    }
  }

  getCacheKey(url) {
    return `configstream_cache_${url}`;
  }

  getExpiryForUrl(url) {
    if (url.includes('metadata')) return this.config.metadataExpiry ?? 120000;
    if (url.includes('proxies')) return this.config.proxiesExpiry ?? 600000;
    if (url.includes('statistics')) return this.config.statsExpiry ?? 300000;
    return this.config.defaultExpiry ?? 300000;
  }

  isExpired(cachedData, expiryMs) {
    if (!cachedData.timestamp) return true;
    const maxAge = expiryMs ?? this.config.defaultExpiry ?? 300000;
    return (Date.now() - cachedData.timestamp) > maxAge;
  }

  isStale(cachedData, expiryMs) {
    if (!cachedData.timestamp) return true;
    const maxAge = expiryMs ?? this.config.defaultExpiry ?? 300000;
    return (Date.now() - cachedData.timestamp) > (maxAge * 0.75);
  }

  get cacheAvailable() {
    if (this._cacheAvailable !== undefined) return this._cacheAvailable;
    this._cacheAvailable = 'indexedDB' in window;
    if (!this._cacheAvailable) this.log.warn('IndexedDB not available.');
    return this._cacheAvailable;
  }

  async clear() {
      // Alias for clearCache
      return this.clearCache();
  }

  async invalidate(url) {
      if (!this.cacheAvailable) return;
      const cacheKey = this.getCacheKey(url);
      try {
          await this.idb.set(cacheKey, null); // Or delete method if available
          this.log.info(`Invalidated cache for ${url}`);
      } catch(e) {
          this.log.error(`Failed to invalidate ${url}`);
      }
  }

  async clearCache() {
    if (this.cacheAvailable) {
        await this.idb.clear();
        this.log.info('Cleared IndexedDB cache store.');
    }
    if ('caches' in window) {
        const keys = await caches.keys();
        await Promise.all(keys.map(key => caches.delete(key)));
        this.log.info('Cleared all standard browser caches.');
    }
  }
}

// Step 5: Create and initialize a global instance
const cacheManager = new CacheManager();
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => cacheManager.init());
} else {
  cacheManager.init();
}

// Export for module usage if needed
if (typeof window !== 'undefined') {
    window.cacheManager = cacheManager;
}
