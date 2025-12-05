// Cache Configuration
// Defines versioning and strategies for the PWA Service Worker.
// Loaded first to establish the global 'cache' configuration object.

(function(global) {
    global.ConfigStreamCache = {
        version: 'v2.0.6',
        precache: [
            '/',
            '/index.html',
            '/proxies.html',
            '/analytics.html',
            '/about.html',
            '/wiki.html',
            '/assets/css/style.css',
            '/assets/js/main.js',
            '/assets/js/utils.js',
            '/assets/js/i18n.js',
            '/assets/svg/favicon.svg'
        ],
        strategies: {
            'default': 'networkFirst',
            'static': 'cacheFirst',
            'api': 'networkOnly'
        }
    };
})(typeof window !== 'undefined' ? window : self);
