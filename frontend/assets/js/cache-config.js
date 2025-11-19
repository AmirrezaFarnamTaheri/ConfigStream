/**
 * Unified Cache Configuration for ConfigStream
 * This single source of truth is used by both sw.js and cache-manager.js
 * 
 * IMPORTANT: This file must load before any script that uses it
 */

(function() {
  'use strict';
  
  // Semantic version for cache invalidation
  // Increment this to force cache refresh across all users
  const VERSION = '1.1.0';
  const CACHE_PREFIX = 'configstream';
  
  // Create cache configuration object
  const config = {
    // Version info
    VERSION: VERSION,
    CACHE_NAME: `${CACHE_PREFIX}-v${VERSION}`,
    
    // Cache duration settings (in milliseconds)
    CACHE_CONFIG: {
      // Metadata changes frequently as new proxies are added
      metadataExpiry: 2 * 60 * 1000,        // 2 minutes
      
      // Proxy list updates every 3 hours via GitHub Actions
      proxiesExpiry: 10 * 60 * 1000,        // 10 minutes
      
      // Statistics are derivative data, can be cached longer
      statsExpiry: 5 * 60 * 1000,           // 5 minutes
      
      // Fallback for unspecified resources
      defaultExpiry: 5 * 60 * 1000,         // 5 minutes
      
      // How long to wait for network before using cache
      networkTimeout: 5000,                 // 5 seconds
      
      // Enable stale-while-revalidate pattern
      staleWhileRevalidate: true
    },
    
    // URL-based caching strategies
    CACHE_STRATEGY: {
      // Always fetch fresh from network, never cache
      // These are dynamic JSON files that change frequently
      networkOnly: [
        'output/metadata.json'
      ],
      
      // Try network first, fall back to cache if offline
      // These update regularly but cache is acceptable if offline
      networkFirst: [
        'output/proxies.json',
        'output/statistics.json',
        'output/vpn_subscription_base64.txt',
        // HTML pages should always be fresh to ensure navigation works
        'index.html',
        'proxies.html',
        'statistics.html'
      ],

      // Use cache first, update in background
      // These are static assets that rarely change
      cacheFirst: [
        'assets/css/style.css',
        'assets/css/state-manager.css',
        'assets/js/utils.js',
        'assets/js/main.js',
        'assets/js/state-manager.js',
        'assets/js/error-handler.js',
        'assets/js/loading-controller.js',
        'assets/js/logo-controller.js',
        'assets/js/cache-manager.js',
        'assets/js/cache-config.js',
        'assets/js/unified-cache.js'
      ]
    },
    
    // Files to pre-cache on service worker installation
    // These are the minimum files needed for offline functionality
    PRECACHE_URLS: [
      'index.html',
      'proxies.html',
      'statistics.html',
      'assets/css/style.css',
      'assets/css/state-manager.css',
      'assets/js/utils.js',
      'assets/js/cache-manager.js',
      'assets/js/cache-config.js',
      'assets/js/state-manager.js',
      'assets/js/main.js',
      'assets/js/unified-cache.js'
    ]
  };
  
  // Export to global scope for service worker
  if (typeof self !== 'undefined' && self.WorkerGlobalScope) {
    // We're in a service worker
    self.ConfigStreamCache = config;
  } else if (typeof window !== 'undefined') {
    // We're in the main browser thread
    window.ConfigStreamCache = config;
  }
  
  // Also export for Node.js testing environments
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = config;
  }
  
  // Freeze to prevent accidental modification
  Object.freeze(config);
  Object.freeze(config.CACHE_CONFIG);
  Object.freeze(config.CACHE_STRATEGY);
  
  console.log(`[CacheConfig] Loaded v${VERSION} successfully`);
})();