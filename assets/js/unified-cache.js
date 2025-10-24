/**
 * Unified Cache Manager for ConfigStream
 * Coordinates service worker cache, localStorage, and memory cache
 * Provides single interface for all caching needs
 */

class UnifiedCacheManager {
  constructor() {
    // Load configuration
    this.config = window.ConfigStreamCache;
    
    if (!this.config) {
      throw new Error('Cache configuration not loaded. Include cache-config.js first.');
    }
    
    // Logging utility
    this.log = {
      info: (msg) => console.log(`[UnifiedCache] ${msg}`),
      warn: (msg) => console.warn(`[UnifiedCache] ${msg}`),
      error: (msg) => console.error(`[UnifiedCache] ${msg}`),
      debug: (msg) => console.debug(`[UnifiedCache] ${msg}`)
    };
    
    // Check feature support
    this.features = {
      serviceWorker: 'serviceWorker' in navigator,
      cacheAPI: 'caches' in window,
      localStorage: this.checkLocalStorage()
    };
    
    this.log.info(`Features: SW=${this.features.serviceWorker}, Cache=${this.features.cacheAPI}, Storage=${this.features.localStorage}`);
    
    // Service worker registration
    this.swRegistration = null;
    
    // Initialize
    this.init();
  }
  
  /**
   * Check if localStorage is available and working
   */
  checkLocalStorage() {
    try {
      const test = '__cache_test__';
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch (error) {
      this.log.warn('localStorage not available');
      return false;
    }
  }
  
  /**
   * Initialize cache manager
   */
  async init() {
    if (this.features.serviceWorker) {
      try {
        const swUrl = new URL('sw.js', document.baseURI).toString();
        const scopeUrl = new URL('.', document.baseURI).toString();
        this.swRegistration = await navigator.serviceWorker.register(swUrl, { scope: scopeUrl });
        this.log.info('Service worker registered');
        
        // Check for updates periodically
        this.startUpdateCheck();
      } catch (error) {
        this.log.error(`Service worker registration failed: ${error.message}`);
      }
    }
  }
  
  /**
   * Periodically check for service worker updates
   */
  startUpdateCheck() {
    setInterval(() => {
      if (this.swRegistration) {
        this.swRegistration.update().catch(error => {
          this.log.debug(`Update check failed: ${error.message}`);
        });
      }
    }, 5 * 60 * 1000); // Every 5 minutes
  }
  
  /**
   * Get data from cache using best available method
   * Priority: Service Worker Cache API → localStorage → null
   * 
   * @param {string} url - URL or key to fetch
   * @param {Object} options - Options
   * @returns {Promise<any>} Cached data or null
   */
  async get(url, options = {}) {
    const { bypassCache = false } = options;
    
    if (bypassCache) {
      return null;
    }
    
    // Try Cache API first (fastest and most reliable)
    if (this.features.cacheAPI) {
      try {
        const response = await caches.match(url);
        if (response) {
          // Check if we should treat this as JSON
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            this.log.debug(`Cache hit (API): ${url}`);
            return data;
          } else {
            const text = await response.text();
            this.log.debug(`Cache hit (API): ${url}`);
            return text;
          }
        }
      } catch (error) {
        this.log.debug(`Cache API error: ${error.message}`);
      }
    }
    
    // Try localStorage second
    if (this.features.localStorage) {
      try {
        const cached = this.getFromLocalStorage(url);
        if (cached && !this.isExpired(cached)) {
          this.log.debug(`Cache hit (localStorage): ${url}`);
          return cached.data;
        }
      } catch (error) {
        this.log.debug(`localStorage error: ${error.message}`);
      }
    }
    
    // No cache hit
    return null;
  }
  
  /**
   * Store data in cache using all available methods
   * 
   * @param {string} url - URL or key to store
   * @param {any} data - Data to cache
   * @param {number} expiryMs - Expiry time in milliseconds (optional)
   * @returns {Promise<boolean>} Success indicator
   */
  async set(url, data, expiryMs = null) {
    let success = false;
    
    // Prepare cache item with expiry metadata
    const cacheItem = {
      data,
      timestamp: Date.now(),
      expiry: expiryMs || this.getExpiryForUrl(url)
    };
    
    // Store in Cache API if available
    if (this.features.cacheAPI) {
      try {
        const cache = await caches.open(this.config.CACHE_NAME);
        
        // Determine content type
        const isJSON = typeof data === 'object';
        const content = isJSON ? JSON.stringify(data) : String(data);
        const contentType = isJSON ? 'application/json' : 'text/plain';
        
        // Create response
        const response = new Response(content, {
          headers: {
            'Content-Type': contentType,
            'X-Cached-At': String(Date.now()),
            'X-Expires-In': String(cacheItem.expiry)
          }
        });
        
        await cache.put(url, response);
        this.log.debug(`Cached (API): ${url}`);
        success = true;
      } catch (error) {
        this.log.warn(`Cache API store failed: ${error.message}`);
      }
    }
    
    // Also store in localStorage as fallback
    if (this.features.localStorage) {
      try {
        this.setInLocalStorage(url, cacheItem);
        this.log.debug(`Cached (localStorage): ${url}`);
        success = true;
      } catch (error) {
        this.log.warn(`localStorage store failed: ${error.message}`);
      }
    }
    
    return success;
  }
  
  /**
   * Get data from localStorage with key prefix
   */
  getFromLocalStorage(url) {
    const key = this.getStorageKey(url);
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : null;
  }
  
  /**
   * Store data in localStorage with key prefix
   */
  setInLocalStorage(url, cacheItem) {
    const key = this.getStorageKey(url);
    localStorage.setItem(key, JSON.stringify(cacheItem));
  }
  
  /**
   * Generate storage key with prefix
   */
  getStorageKey(url) {
    return `cs_cache_${url}`;
  }
  
  /**
   * Check if cached item has expired
   */
  isExpired(cacheItem) {
    if (!cacheItem.timestamp || !cacheItem.expiry) {
      return true;
    }
    
    const age = Date.now() - cacheItem.timestamp;
    return age > cacheItem.expiry;
  }
  
  /**
   * Get appropriate expiry time for URL
   */
  getExpiryForUrl(url) {
    const config = this.config.CACHE_CONFIG;
    
    if (url.includes('metadata')) {
      return config.metadataExpiry;
    }
    
    if (url.includes('proxies')) {
      return config.proxiesExpiry;
    }
    
    if (url.includes('statistics')) {
      return config.statsExpiry;
    }
    
    return config.defaultExpiry;
  }
  
  /**
   * Clear all caches
   */
  async clearAll() {
    let cleared = 0;
    
    // Clear Cache API
    if (this.features.cacheAPI) {
      try {
        const cacheNames = await caches.keys();
        await Promise.all(
          cacheNames.map(name => caches.delete(name))
        );
        cleared += cacheNames.length;
        this.log.info(`Cleared ${cacheNames.length} cache(s) from Cache API`);
      } catch (error) {
        this.log.error(`Failed to clear Cache API: ${error.message}`);
      }
    }
    
    // Clear localStorage
    if (this.features.localStorage) {
      try {
        const keys = [];
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (key && key.startsWith('cs_cache_')) {
            keys.push(key);
          }
        }
        
        keys.forEach(key => localStorage.removeItem(key));
        cleared += keys.length;
        this.log.info(`Cleared ${keys.length} item(s) from localStorage`);
      } catch (error) {
        this.log.error(`Failed to clear localStorage: ${error.message}`);
      }
    }
    
    return cleared;
  }
  
  /**
   * Get cache statistics
   */
  async getStats() {
    const stats = {
      cacheAPI: {
        available: this.features.cacheAPI,
        caches: 0,
        estimatedSize: 0
      },
      localStorage: {
        available: this.features.localStorage,
        items: 0,
        estimatedSize: 0
      }
    };
    
    // Cache API stats
    if (this.features.cacheAPI) {
      try {
        const cacheNames = await caches.keys();
        stats.cacheAPI.caches = cacheNames.length;
        
        // Estimate size (not perfect but gives an idea)
        if ('storage' in navigator && 'estimate' in navigator.storage) {
          const estimate = await navigator.storage.estimate();
          stats.cacheAPI.estimatedSize = estimate.usage || 0;
        }
      } catch (error) {
        this.log.debug(`Failed to get Cache API stats: ${error.message}`);
      }
    }
    
    // localStorage stats
    if (this.features.localStorage) {
      try {
        let size = 0;
        let count = 0;
        
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (key && key.startsWith('cs_cache_')) {
            count++;
            const value = localStorage.getItem(key);
            size += value ? value.length : 0;
          }
        }
        
        stats.localStorage.items = count;
        stats.localStorage.estimatedSize = size;
      } catch (error) {
        this.log.debug(`Failed to get localStorage stats: ${error.message}`);
      }
    }
    
    return stats;
  }
  
  /**
   * Preload critical resources
   */
  async preload(urls) {
    if (!Array.isArray(urls)) {
      urls = [urls];
    }
    
    this.log.info(`Preloading ${urls.length} resources`);
    
    const results = await Promise.allSettled(
      urls.map(async (url) => {
        try {
          const response = await fetch(url);
          if (response.ok) {
            await this.set(url, await response.text());
            return { url, success: true };
          }
          return { url, success: false, reason: `HTTP ${response.status}` };
        } catch (error) {
          return { url, success: false, reason: error.message };
        }
      })
    );
    
    const successful = results.filter(r => r.status === 'fulfilled' && r.value.success).length;
    this.log.info(`Preloaded ${successful}/${urls.length} resources`);
    
    return results;
  }
}

// Create global instance
window.unifiedCache = new UnifiedCacheManager();

console.log('✅ Unified Cache Manager initialized');