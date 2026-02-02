// Service Worker for ConfigStream
// Uses configuration from cache-config.js

// Import shared configuration
importScripts('assets/js/cache-config.js'); // VERSION/CACHE_NAME is rewritten on deploy

// Access config from global scope (set by cache-config.js)
const config = self.ConfigStreamCache || {};
const VERSION = config.VERSION || 'ERR_NO_VERSION'; // Fail loudly if config missing
const CACHE_NAME = config.CACHE_NAME || `configstream-v${VERSION}`;
const ASSETS_TO_CACHE = config.PRECACHE_URLS || [
  'index.html',
  'proxies.html',
  'analytics.html',
  'about.html',
  'wiki.html',
  'assets/css/style.css',
  'assets/js/main.js',
  'assets/js/utils.js'
];

console.log(`[ServiceWorker] Initializing v${VERSION} (${CACHE_NAME})`);

// Install Event: Cache Core Assets
self.addEventListener('install', (event) => {
  self.skipWaiting(); // Force activation
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log(`[ServiceWorker] Pre-caching ${ASSETS_TO_CACHE.length} assets`);
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

// Activate Event: Clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          // Check if cache name starts with prefix but doesn't match current version
          // Assuming prefix "configstream-v" from cache-config.js logic
          if (cacheName.startsWith('configstream-v') && cacheName !== CACHE_NAME) {
            console.log('[ServiceWorker] Removing old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event: Network First for Data, Cache First for Assets
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  const mode = config.CACHE_STRATEGY || 'stale-while-revalidate';

  const isData = url.pathname.endsWith('.json') || url.pathname.includes('/api/');
  const normalizedMode = (typeof mode === 'string') ? mode : 'stale-while-revalidate';
  const effectiveMode = isData ? 'network-first' : normalizedMode;

  if (effectiveMode === 'network-first') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Clone response to cache it for offline usage
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
          return response;
        })
        .catch(() => {
          // If offline, try cache
          return caches.match(event.request);
        })
    );
    return;
  }

  // Strategy 2: Cache First, Revalidate (Static Assets)
  // Default fallback for everything else
  event.respondWith(
    caches.match(event.request)
      .then((cachedResponse) => {
        if (cachedResponse) {
            // Return cached response immediately
            // Background update (Stale-While-Revalidate)
            if (config.CACHE_CONFIG && config.CACHE_CONFIG.staleWhileRevalidate) {
                fetch(event.request).then(response => {
                    if(response && response.status === 200) {
                         caches.open(CACHE_NAME).then(cache => cache.put(event.request, response));
                    }
                }).catch(err => {}); // Eat errors for background fetch
            }
            return cachedResponse;
        }
        // Cache miss -> Network
        return fetch(event.request).then(response => {
             // Cache new static assets
             if (response && response.status === 200) {
                 const responseClone = response.clone();
                 caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseClone));
             }
             return response;
        });
      })
  );
});
