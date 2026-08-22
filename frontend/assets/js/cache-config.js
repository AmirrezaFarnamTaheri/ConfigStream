// Cache Configuration
// Defines versions, strategies, and TTLs for the application

(function(global) {
    global.ConfigStreamCache = {
        VERSION: 'v3.2.0', // Synced with pyproject.toml
        CACHE_PREFIX: 'configstream-cache-',
        CACHE_NAME: 'configstream-cache-v3.2.0',

        // Cache Strategies
        CACHE_STRATEGY: {
            networkFirst: ['.json', '/api/'],
            staleWhileRevalidate: true
        }
    };
    if (global.ConfigStreamLogger) {
        global.ConfigStreamLogger.info("✅ ConfigStream Cache Config Loaded");
    }
})(typeof window !== 'undefined' ? window : self);
