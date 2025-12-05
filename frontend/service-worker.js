const CACHE_NAME = 'configstream-v4';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './proxies.html',
  './analytics.html',
  './about/',
  './wiki/',
  './assets/css/style.css',
  './assets/css/loading.css',
  './assets/css/error-handler.css',
  './assets/css/state-manager.css',
  './assets/js/main.js',
  './assets/js/utils.js',
  './assets/js/i18n.js',
  './assets/js/cache-config.js',
  './assets/js/cache-manager.js',
  './assets/js/error-handler.js',
  './assets/js/loading-controller.js',
  './assets/js/state-manager.js',
  './assets/svg/favicon.svg',
  './assets/images/favicon.ico'
];

// Install Event: Cache Core Assets
self.addEventListener('install', (event) => {
  self.skipWaiting(); // Force activation
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[ServiceWorker] Pre-caching offline assets');
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
          if (cacheName !== CACHE_NAME) {
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

  // Strategy 1: Network First (for fresh data like proxies.json, metadata.json)
  if (url.pathname.endsWith('.json') || url.pathname.includes('/api/')) {
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

  // Strategy 2: Cache First, Revalidate (for static assets)
  event.respondWith(
    caches.match(event.request)
      .then((cachedResponse) => {
        if (cachedResponse) {
            // Return cached but fetch new version in background
            fetch(event.request).then(response => {
                if(response && response.status === 200) {
                     caches.open(CACHE_NAME).then(cache => cache.put(event.request, response));
                }
            }).catch(err => {}); // Eat errors for background fetch
            return cachedResponse;
        }
        return fetch(event.request);
      })
  );
});
