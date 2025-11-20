const CACHE_NAME = 'configstream-v1';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './proxies.html',
  './statistics.html',
  './assets/css/style.css',
  './assets/css/state-manager.css',
  './assets/css/error-handler.css',
  './assets/css/loading.css',
  './assets/js/main.js',
  './assets/js/utils.js',
  './assets/js/cache-manager.js',
  './assets/js/state-manager.js',
  './assets/svg/logo-loading.svg'
];

// Install Event
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

// Activate Event
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(
        keyList.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
});

// Fetch Event
self.addEventListener('fetch', (event) => {
  // Bypass cache for API requests or if we are offline
  if (event.request.url.includes('/api/') || event.request.url.includes('/ws/')) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
