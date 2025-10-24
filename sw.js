/**
* Service Worker for ConfigStream
 * Handles offline support, background sync, and intelligent caching
 * 
 * This file is executed in a separate worker thread by the browser.
 * It cannot directly access the DOM but can intercept network requests.
 */

// Import cache configuration first
// In service workers, importScripts() is synchronous and blocking
try {
  importScripts('./assets/js/cache-config.js');
} catch (error) {
  console.error('[SW] FATAL: Cannot load cache configuration:', error);
  // Without configuration, we cannot function properly
  throw new Error('Service Worker initialization failed');
}

// Verify configuration loaded successfully
if (!self.ConfigStreamCache) {
  throw new Error('[SW] Cache configuration not available');
}

const config = self.ConfigStreamCache;
const scopeUrl = new URL(self.registration.scope);
const scopePathname = scopeUrl.pathname.endsWith('/')
  ? scopeUrl.pathname
  : `${scopeUrl.pathname}/`;

// Logging utility with consistent prefixes
const log = {
  info: (msg) => console.log(`[SW ${config.VERSION}] ${msg}`),
  warn: (msg) => console.warn(`[SW ${config.VERSION}] ${msg}`),
  error: (msg) => console.error(`[SW ${config.VERSION}] ${msg}`),
  debug: (msg) => console.debug(`[SW ${config.VERSION}] ${msg}`)
};

log.info('Service Worker loaded successfully');

/**
 * INSTALL EVENT
 * Triggered when the service worker is first installed or updated
 */
self.addEventListener('install', (event) => {
  log.info('Installing...');
  
  event.waitUntil(
    (async () => {
      try {
        const cache = await caches.open(config.CACHE_NAME);

        // Pre-cache essential files for offline support
        const urlsToCache = (config.PRECACHE_URLS || []).map((resource) => {
          return new URL(resource, scopeUrl).toString();
        });
        
        if (urlsToCache.length === 0) {
          log.warn('No URLs configured for pre-caching');
          return;
        }
        
        log.info(`Pre-caching ${urlsToCache.length} URLs`);

        for (const urlToCache of urlsToCache) {
          try {
            await cache.add(urlToCache);
            log.debug(`Pre-cached: ${urlToCache}`);
          } catch (error) {
            log.warn(`Skipping precache for ${urlToCache}: ${error.message}`);
          }
        }
        
        log.info('Pre-caching completed');
        
        // Skip waiting phase and activate immediately
        // This ensures users get the new service worker right away
        await self.skipWaiting();
        
        log.info('Service Worker installed and ready');
      } catch (error) {
        log.error(`Installation failed: ${error.message}`);
        // Re-throw to prevent broken service worker activation
        throw error;
      }
    })()
  );
});

/**
 * ACTIVATE EVENT
 * Triggered when the service worker is activated
 * This is where we clean up old caches
 */
self.addEventListener('activate', (event) => {
  log.info('Activating...');
  
  event.waitUntil(
    (async () => {
      try {
        // Get list of all cache names
        const cacheNames = await caches.keys();
        
        // Find old ConfigStream caches to delete
        const oldCaches = cacheNames.filter(cacheName => 
          cacheName.startsWith('configstream-') && 
          cacheName !== config.CACHE_NAME
        );
        
        if (oldCaches.length > 0) {
          log.info(`Cleaning up ${oldCaches.length} old cache(s)`);
          await Promise.all(
            oldCaches.map(cacheName => {
              log.debug(`Deleting cache: ${cacheName}`);
              return caches.delete(cacheName);
            })
          );
        }
        
        // Take control of all open pages immediately
        // Without this, users would need to refresh to use new SW
        await self.clients.claim();
        
        log.info('Activated and controlling all pages');
      } catch (error) {
        log.error(`Activation failed: ${error.message}`);
      }
    })()
  );
});

/**
 * FETCH EVENT
 * Intercepts all network requests and applies caching strategies
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Only handle GET requests for our own domain
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip non-HTTP(S) requests (like chrome-extension://)
  if (!url.protocol.startsWith('http')) {
    return;
  }
  
  // Skip requests to other domains
  if (url.origin !== self.location.origin) {
    return;
  }
  
  // Determine caching strategy based on URL
  const localPath = toLocalPath(url);
  const strategy = getCacheStrategy(localPath);

  // Respond with appropriate strategy
  event.respondWith(handleRequest(event, request, strategy, url, localPath));
});

/**
 * Determine which caching strategy to use for a URL
 */
function getCacheStrategy(pathname) {
  const strategies = config.CACHE_STRATEGY;
  
  // Check each strategy list
  if (strategies.networkOnly?.some(path => pathname === path)) {
    return 'networkOnly';
  }
  
  if (strategies.networkFirst?.some(path => pathname === path)) {
    return 'networkFirst';
  }
  
  if (strategies.cacheFirst?.some(path => pathname === path)) {
    return 'cacheFirst';
  }
  
  // Default to network-first for unknown resources
  return 'networkFirst';
}

/**
 * Handle request with specified caching strategy
 */
async function handleRequest(fetchEvent, request, strategy, url, localPath) {
  try {
    switch (strategy) {
      case 'networkOnly':
        return await networkOnly(request, url);

      case 'networkFirst':
        return await networkFirst(request, url);

      case 'cacheFirst':
        return await cacheFirst(fetchEvent, request, url);
      
      default:
        log.warn(`Unknown strategy: ${strategy}, using network-first`);
        return await networkFirst(request, url);
    }
  } catch (error) {
    log.error(`Request failed: ${error.message}`);
    
    // Try to return a cached version as last resort
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      log.info(`Serving stale cache for ${localPath}`);
      return cachedResponse;
    }
    
    // Return offline page if we have it
    const offlinePage = await caches.match('/offline.html');
    if (offlinePage) {
      return offlinePage;
    }
    
    // Last resort: generic error response
    return createOfflineResponse();
  }
}

/**
 * Network-only strategy: Always fetch from network
 */
async function networkOnly(request, url) {
  log.debug(`[networkOnly] ${url.pathname}`);
  return await fetch(request);
}

/**
 * Network-first strategy: Try network, fall back to cache
 */
async function networkFirst(request, url) {
  try {
    const networkResponse = await fetch(request);
    
    // Cache successful responses
    if (networkResponse && networkResponse.ok) {
      const cache = await caches.open(config.CACHE_NAME);
      // Clone because response can only be read once
      cache.put(request, networkResponse.clone());
      log.debug(`[networkFirst] Fresh: ${url.pathname}`);
      return networkResponse;
    }
    
    // Network returned error, try cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      log.warn(`[networkFirst] Network error, using cache: ${url.pathname}`);
      return cachedResponse;
    }
    
    return networkResponse;
  } catch (error) {
    // Network completely failed, use cache
    log.warn(`[networkFirst] Network failed, trying cache: ${url.pathname}`);
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    throw error;
  }
}

/**
 * Cache-first strategy: Use cache if available, fetch otherwise
 */
async function cacheFirst(fetchEvent, request, url) {
  // Try cache first
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    log.debug(`[cacheFirst] Cache hit: ${url.pathname}`);

    // Update cache in background (stale-while-revalidate)
    if (config.CACHE_CONFIG.staleWhileRevalidate) {
      fetchEvent.waitUntil(
        (async () => {
          try {
            const freshResponse = await fetch(request);
            if (freshResponse && freshResponse.ok) {
              const cache = await caches.open(config.CACHE_NAME);
              await cache.put(request, freshResponse);
              log.debug(`[cacheFirst] Background refresh: ${url.pathname}`);
            }
          } catch (error) {
            // Silently fail background refresh
            log.debug(`[cacheFirst] Background refresh failed: ${url.pathname}`);
          }
        })()
      );
    }
    
    return cachedResponse;
  }
  
  // Cache miss, fetch from network
  log.debug(`[cacheFirst] Cache miss, fetching: ${url.pathname}`);
  const networkResponse = await fetch(request);
  
  // Cache successful responses
  if (networkResponse && networkResponse.ok) {
    const cache = await caches.open(config.CACHE_NAME);
    cache.put(request, networkResponse.clone());
  }
  
  return networkResponse;
}

/**
 * Create a simple offline response
 */
function createOfflineResponse() {
  const html = `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Offline - ConfigStream</title>
      <style>
        body {
          font-family: system-ui, -apple-system, sans-serif;
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          margin: 0;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          text-align: center;
          padding: 20px;
        }
        .container {
          max-width: 500px;
        }
        h1 {
          font-size: 3em;
          margin: 0 0 0.5em;
        }
        p {
          font-size: 1.2em;
          line-height: 1.6;
        }
        button {
          margin-top: 2em;
          padding: 1em 2em;
          font-size: 1em;
          border: 2px solid white;
          background: transparent;
          color: white;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.3s;
        }
        button:hover {
          background: white;
          color: #667eea;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>📡 You're Offline</h1>
        <p>This page isn't available in your cache yet. Connect to the internet and try again.</p>
        <button onclick="location.reload()">Try Again</button>
      </div>
    </body>
    </html>
  `;
  
  return new Response(html, {
    status: 503,
    statusText: 'Service Unavailable',
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store'
    }
  });
}

log.info('Service Worker ready and waiting for events');
function toLocalPath(url) {
  const pathname = url.pathname;
  if (pathname.startsWith(scopePathname)) {
    const relative = pathname.slice(scopePathname.length);
    const cleaned = relative.startsWith('/') ? relative.slice(1) : relative;
    return cleaned === '' ? 'index.html' : cleaned;
  }
  const fallback = pathname.startsWith('/') ? pathname.slice(1) : pathname;
  return fallback === '' ? 'index.html' : fallback;
}
