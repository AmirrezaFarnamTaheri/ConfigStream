const CACHE_NAME = 'configstream-v1';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './proxies.html',
  './analytics.html',
  './assets/css/style.css',
  './assets/css/loading.css',
  './assets/js/main.js',
  './assets/js/utils.js',
  './assets/svg/favicon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

self.addEventListener('fetch', (event) => {
  // Network first for JSON/API data, Cache first for static assets
  if (event.request.url.includes('.json')) {
      event.respondWith(
        fetch(event.request)
          .catch(() => caches.match(event.request))
      );
  } else {
      event.respondWith(
        caches.match(event.request)
          .then((response) => response || fetch(event.request))
      );
  }
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
