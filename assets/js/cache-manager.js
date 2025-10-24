/**
 * Cache Manager for ConfigStream
 * Manages cache expiry, stale-while-revalidate, and data freshness
 * Runs in the main browser thread (NOT in the service worker)
 */

// Step 1: Verify that cache configuration is available
// This assumes cache-config.js was loaded BEFORE this script in index.html
if (!globalThis.ConfigStreamCache) {
  console.error('[CacheManager] FATAL: Cache configuration not loaded! Make sure cache-config.js is loaded first.');
  throw new Error('Cache configuration unavailable');
}

// Step 2: Get configuration from the shared namespace
const config = globalThis.ConfigStreamCache;

// Step 3: Initialize the cache manager
class CacheManager {
  constructor() {
    this.cacheName = config.CACHE_NAME;
    this.config = config.CACHE_CONFIG;
    this.strategy = config.CACHE_STRATEGY;
    this.log = this.createLogger();
    this.initialized = false;
    this._cacheAvailable = undefined;

    this.log.info('CacheManager initialized with cache name: ' + this.cacheName);
  }

  /**
   * Create a logger function for consistent debugging
   */
  createLogger() {
    return {
      info: (msg) => console.log(`[CacheManager] ${msg}`),
      warn: (msg) => console.warn(`[CacheManager] ${msg}`),
      error: (msg) => console.error(`[CacheManager] ${msg}`)
    };
  }

  /**
   * Initialize the cache manager and register service worker
   */
  async init() {
    if (this.initialized) {
      this.log.warn('Already initialized, skipping...');
      return;
    }

    try {
      // Check if service workers are supported
      if (!('serviceWorker' in navigator)) {
        this.log.error('Service Workers not supported in this browser');
        return;
      }

      // Register the service worker relative to the current document so it works on GitHub Pages
      const swUrl = new URL('sw.js', document.baseURI).toString();
      const scopeUrl = new URL('.', document.baseURI).toString();

      const registration = await navigator.serviceWorker.register(swUrl, {
        scope: scopeUrl
      });

      this.log.info('Service Worker registered successfully');
      this.swRegistration = registration;

      // Listen for updates to the service worker
      registration.addEventListener('updatefound', () => {
        this.log.info('Service Worker update found');
        const newWorker = registration.installing;

        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            this.log.info('New Service Worker installed, ready to activate');
            this.notifyUpdate();
          }
        });
      });

      // Check for updates periodically
      this.startUpdateCheck();

      this.initialized = true;
    } catch (error) {
      this.log.error('Failed to initialize: ' + error.message);
    }
  }

  /**
   * Start checking for service worker updates periodically
   */
  startUpdateCheck() {
    // Check for updates every 5 minutes
    setInterval(() => {
      if (this.swRegistration) {
        this.swRegistration.update().catch((error) => {
          this.log.warn('Failed to check for updates: ' + error.message);
        });
      }
    }, 5 * 60 * 1000);
  }

  /**
   * Notify the user that an update is available
   */
  notifyUpdate() {
    // Dispatch a custom event that your app can listen for
    window.dispatchEvent(new CustomEvent('sw-update-ready'));
  }

  /**
   * Fetch data with cache-aware behavior
   * This respects the cache expiry times set in configuration
   */
  async fetchWithCache(url, options = {}) {
    const { bypassCache = false, expiry = null } = options;

    if (bypassCache) {
      return this.fetchFresh(url);
    }

    try {
      // Check if we have cached data and if it's still fresh
      const cachedData = await this.getCachedData(url);
      const expiryMs = expiry ?? cachedData?.expiry ?? this.getExpiryForUrl(url);

      if (cachedData && !this.isExpired(cachedData, expiryMs)) {
        this.log.info(`Using cached data for ${url}`);

        // If stale-while-revalidate is enabled, fetch fresh data in the background
        if (this.config.staleWhileRevalidate && this.isStale(cachedData, expiryMs)) {
          this.log.info(`Revalidating in background: ${url}`);
          this.fetchFresh(url).catch((error) => {
            this.log.warn(`Background revalidation failed: ${error.message}`);
          });
        }

        return cachedData.data;
      }

      // Cache miss or expired, fetch fresh
      return await this.fetchFresh(url);
    } catch (error) {
      this.log.error(`fetchWithCache failed for ${url}: ${error.message}`);
      throw error;
    }
  }

  /**
   * Fetch fresh data from the network
   */
  async fetchFresh(url) {
    this.log.info(`Fetching fresh data: ${url}`);

    const timeout = this.config.networkTimeout || 5000;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        signal: controller.signal,
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // Cache the fresh data
      await this.cacheData(url, data);

      return data;
    } catch (error) {
      clearTimeout(timeoutId);
      this.log.error(`fetchFresh failed for ${url}: ${error.message}`);
      throw error;
    }
  }

  /**
   * Get data from the browser cache
   */
  async getCachedData(url) {
    if (!this.cacheAvailable) {
      return null;
    }

    try {
      const cacheKey = this.getCacheKey(url);
      const cachedItem = localStorage.getItem(cacheKey);

      if (!cachedItem) {
        return null;
      }

      const parsed = JSON.parse(cachedItem);

      return {
        data: parsed.data,
        timestamp: parsed.timestamp,
        expiry: parsed.expiry
      };
    } catch (error) {
      this.log.error(`Failed to get cached data for ${url}: ${error.message}`);
      return null;
    }
  }

  /**
   * Store data in the browser cache
   */
  async cacheData(url, data) {
    if (!this.cacheAvailable) {
      return false;
    }

    try {
      const cacheKey = this.getCacheKey(url);
      const timestamp = Date.now();
      const expiry = this.getExpiryForUrl(url);

      const cacheItem = {
        data,
        timestamp,
        expiry
      };

      localStorage.setItem(cacheKey, JSON.stringify(cacheItem));
      return true;
    } catch (error) {
      this.log.error(`Failed to cache data for ${url}: ${error.message}`);
      return false;
    }
  }

  getCacheKey(url) {
    return `configstream_cache_${url}`;
  }

  /**
   * Determine the appropriate cache expiry time for a URL
   */
  getExpiryForUrl(url) {
    if (url.includes('metadata')) {
      return this.config.metadataExpiry ?? 2 * 60 * 1000;
    }
    if (url.includes('proxies')) {
      return this.config.proxiesExpiry ?? 10 * 60 * 1000;
    }
    if (url.includes('statistics')) {
      return this.config.statsExpiry ?? 5 * 60 * 1000;
    }

    return this.config.defaultExpiry ?? 5 * 60 * 1000;
  }

  /**
   * Check if cached data has expired
   */
  isExpired(cachedData, expiryMs) {
    if (!cachedData.timestamp) {
      return true;
    }

    const maxAge = expiryMs ?? this.config.defaultExpiry ?? 5 * 60 * 1000;
    const age = Date.now() - cachedData.timestamp;
    return age > maxAge;
  }

  /**
   * Check if cached data is stale (but not expired)
   * Used for stale-while-revalidate
   */
  isStale(cachedData, expiryMs) {
    if (!cachedData.timestamp) {
      return true;
    }

    const age = Date.now() - cachedData.timestamp;
    const maxAge = expiryMs ?? this.config.defaultExpiry ?? 5 * 60 * 1000;
    const staleThreshold = maxAge * 0.75;

    return age > staleThreshold;
  }

  get cacheAvailable() {
    if (typeof this._cacheAvailable === 'boolean') {
      return this._cacheAvailable;
    }

    try {
      const test = '__cache_test__';
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      this._cacheAvailable = true;
    } catch (error) {
      this._cacheAvailable = false;
      this.log.warn(`LocalStorage unavailable: ${error.message}`);
    }

    return this._cacheAvailable;
  }

  /**
   * Clear all caches
   */
  async clearCache() {
    if ('caches' in window) {
      try {
        const cacheNames = await caches.keys();
        await Promise.all(
          cacheNames.map((name) => {
            this.log.info(`Deleting cache: ${name}`);
            return caches.delete(name);
          })
        );
        this.log.info('Cleared registered caches');
      } catch (error) {
        this.log.error(`Failed to clear caches: ${error.message}`);
      }
    }

    if (this.cacheAvailable) {
      const keysToRemove = [];
      for (let i = 0; i < localStorage.length; i += 1) {
        const key = localStorage.key(i);
        if (key && key.startsWith('configstream_cache_')) {
          keysToRemove.push(key);
        }
      }

      keysToRemove.forEach((key) => localStorage.removeItem(key));
      const removedLabel = keysToRemove.length === 1 ? 'entry' : 'entries';
      this.log.info(`Cleared ${keysToRemove.length} localStorage cache ${removedLabel}`);
    }
  }

  /**
   * Get cache statistics
   */
  async getCacheStats() {
    if (!('caches' in window)) {
      return null;
    }

    try {
      const cacheNames = await caches.keys();
      const stats = {
        totalCaches: cacheNames.length,
        currentCache: this.cacheName,
        caches: {}
      };

      for (const name of cacheNames) {
        const cache = await caches.open(name);
        const keys = await cache.keys();
        stats.caches[name] = keys.length;
      }

      return stats;
    } catch (error) {
      this.log.error(`Failed to get cache stats: ${error.message}`);
      return null;
    }
  }
}

// Step 4: Create a global instance
const cacheManager = new CacheManager();

// Step 5: Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    cacheManager.init().catch((error) => {
      console.error('Failed to initialize CacheManager:', error);
    });
  });
} else {
  cacheManager.init().catch((error) => {
    console.error('Failed to initialize CacheManager:', error);
  });
}
