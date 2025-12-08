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
    // Note: These are fallback durations. The UpdateDetector actively
    // polls for changes every 4 minutes and invalidates cache when updates are detected.
    CACHE_CONFIG: {
      // Update status check (lightweight HEAD/timestamp check)
      updateStatusExpiry: 4 * 60 * 1000,    // 4 minutes (polling interval)

      // Metadata changes when pipeline runs or retest completes
      metadataExpiry: 5 * 60 * 1000,        // 5 minutes

      // Proxy list updates when pipeline/retest generates new data
      proxiesExpiry: 10 * 60 * 1000,        // 10 minutes

      // Statistics are derivative data, updated with metadata
      statsExpiry: 5 * 60 * 1000,           // 5 minutes

      // Fallback for unspecified resources
      defaultExpiry: 5 * 60 * 1000,         // 5 minutes

      // How long to wait for network before using cache
      networkTimeout: 5000,                 // 5 seconds

      // Enable stale-while-revalidate pattern
      // Serves cached data immediately, fetches fresh data in background
      staleWhileRevalidate: true,

      // Smart update detection enabled
      // UpdateDetector polls every 4 minutes and triggers cache invalidation
      smartUpdateDetection: true
    },
    
    // URL-based caching strategies
    CACHE_STRATEGY: {
      // Always fetch fresh from network, never cache
      // Reserved for truly dynamic content that must never be cached
      networkOnly: [
      ],

      // Try network first, fall back to cache if offline
      // These update regularly but cache is acceptable if offline
      networkFirst: [
        (window.ROOT_PATH || '') + 'metadata.json',
        (window.ROOT_PATH || '') + 'proxies.json',
        (window.ROOT_PATH || '') + 'statistics.json',
        (window.ROOT_PATH || '') + 'vpn_subscription_base64.txt',
        // HTML pages should always be fresh to ensure navigation works
        'index.html',
        'proxies.html',
        'analytics.html'
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
      'analytics.html',
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
