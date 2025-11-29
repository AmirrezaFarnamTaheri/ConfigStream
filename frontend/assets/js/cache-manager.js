/**
 * Cache Manager for ConfigStream
 * Manages cache expiry, stale-while-revalidate, and data freshness
 * Uses IndexedDB for robust client-side storage of large datasets.
 */

// Step 1: Verify that cache configuration is available
if (!globalThis.ConfigStreamCache) {
  console.error('[CacheManager] FATAL: Cache configuration not loaded!');
  throw new Error('Cache configuration unavailable');
}

// Step 2: Get configuration from the shared namespace
const config = globalThis.ConfigStreamCache;

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
      info: (msg) => console.log(`[IDBHelper] ${msg}`),
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
    this.cacheName = config.CACHE_NAME;
    this.config = config.CACHE_CONFIG;
    this.strategy = config.CACHE_STRATEGY;
    this.log = this.createLogger();
    this.initialized = false;
    this._cacheAvailable = undefined;
    this.idb = new IDBHelper('ConfigStreamDB', 'apiCache');
  }

  createLogger() {
    return {
      info: (msg) => console.log(`[CacheManager] ${msg}`),
      warn: (msg) => console.warn(`[CacheManager] ${msg}`),
      error: (msg) => console.error(`[CacheManager] ${msg}`),
    };
  }

  async init() {
    if (this.initialized) return;

    try {
      if ('serviceWorker' in navigator) {
        const swUrl = new URL('sw.js', document.baseURI).toString();

        // Audit: Check if service worker file exists before registering
        try {
            const check = await fetch(swUrl, { method: 'HEAD' });
            if (!check.ok) {
                this.log.warn('Service Worker file not found, skipping registration.');
                return;
            }
        } catch (e) {
            this.log.warn('Could not verify Service Worker existence.');
            return;
        }

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
      return cachedItem ? { data: cachedItem.data, timestamp: cachedItem.timestamp, expiry: cachedItem.expiry } : null;
    } catch (error) {
      this.log.error(`Failed to get cached data for ${url}: ${error.message}`);
      return null;
    }
  }

  async cacheData(url, data) {
    if (!this.cacheAvailable) return false;
    try {
      const cacheKey = this.getCacheKey(url);
      const cacheItem = { data, timestamp: Date.now(), expiry: this.getExpiryForUrl(url) };
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
