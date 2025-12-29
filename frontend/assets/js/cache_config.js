// Cache Configuration
// Defines versions, strategies, and TTLs for the application

(function(global) {
    global.ConfigStreamCache = {
        VERSION: 'v1.0.0', // Increment this to bust cache
        CACHE_NAME: 'configstream-cache-v1',

        // Cache Strategies
        CACHE_STRATEGY: 'stale-while-revalidate', // or 'network-first'

        // Time-to-Live (TTL) Configuration (in milliseconds)
        CACHE_CONFIG: {
            staleWhileRevalidate: true,
            networkTimeout: 5000,

            // Specific expiry times
            metadataExpiry: 2 * 60 * 1000,      // 2 minutes for metadata
            proxiesExpiry: 10 * 60 * 1000,      // 10 minutes for proxy lists
            statsExpiry: 5 * 60 * 1000,         // 5 minutes for statistics
            defaultExpiry: 5 * 60 * 1000        // 5 minutes default
        }
    };
    if (global.ConfigStreamLogger) {
        global.ConfigStreamLogger.info("✅ ConfigStream Cache Config Loaded");
    }
})(typeof window !== 'undefined' ? window : self);
