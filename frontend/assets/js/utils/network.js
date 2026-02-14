/**
 * Network and Caching utilities
 * Integrates with CacheManager if available, otherwise falls back to LocalStorage
 */

// Centralized prefix
const CACHE_PREFIX = 'configstream_cache_';

function getCacheBust() {
  return `?cb=${Date.now()}`;
}

async function getFromStorage(key) {
  // Use CacheManager (IndexedDB) if available for better performance
  if (window.cacheManager && window.cacheManager.cacheAvailable) {
      const url = getUrlForKey(key);
      const cached = await window.cacheManager.getCachedData(url);
      if (!cached) return null;

      // Respect CacheManager expiry semantics when IndexedDB is used
      const expiryMs = cached.expiry ?? window.cacheManager.getExpiryForUrl(url);
      if (window.cacheManager.isExpired(cached, expiryMs)) {
        return null;
      }

      return cached.data;
  }

  // Fallback to LocalStorage
  try {
    const item = localStorage.getItem(CACHE_PREFIX + key);
    if (!item) return null;
    const parsed = JSON.parse(item);
    if (Date.now() < parsed.expiry) {
      return parsed.data;
    } else {
      localStorage.removeItem(CACHE_PREFIX + key);
      return null;
    }
  } catch (e) {
    console.warn('Cache read error', e);
    return null;
  }
}

async function saveToStorage(key, data, expiryDuration) {
  // Use CacheManager if available
  if (window.cacheManager && window.cacheManager.cacheAvailable) {
      const url = getUrlForKey(key);
      // CacheManager handles expiry internally via its own config
      await window.cacheManager.cacheData(url, data);
      return;
  }
  // Fallback
  try {
    const payload = {
      data: data,
      expiry: Date.now() + expiryDuration
    };
    localStorage.setItem(CACHE_PREFIX + key, JSON.stringify(payload));
  } catch (e) {
    console.warn('Cache write error', e);
  }
}

function getUrlForKey(key) {
    const root = window.ROOT_PATH || '';
    if (key === 'metadata') return root + 'metadata.json';
    if (key === 'proxies') return root + 'proxies.json';
    // [UNIFIED] statistics now points to metadata.json - single source of truth
    if (key === 'statistics') return root + 'metadata.json';
    return key;
}

function clearCache() {
  if (window.cacheManager && window.cacheManager.clearCache) {
      window.cacheManager.clearCache();
  }
  Object.keys(localStorage).forEach(key => {
    if (key.startsWith(CACHE_PREFIX)) {
      localStorage.removeItem(key);
    }
  });
}

async function fetchWithRetry(url, retries = 3, delay = 1000) {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Accept': 'application/json', 'Cache-Control': 'no-cache' }
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      return response;
    } catch (error) {
      if (i < retries - 1) {
        console.warn(`Fetch attempt ${i + 1} failed, retrying in ${delay}ms:`, error.message);
        await new Promise(resolve => setTimeout(resolve, delay));
        delay = Math.min(delay * 2, 8000);
      } else {
        throw error;
      }
    }
  }
}

async function getStaleFromStorage(key) {
  if (window.cacheManager && window.cacheManager.cacheAvailable) {
    const url = getUrlForKey(key);
    const cached = await window.cacheManager.getCachedData(url);
    if (cached) return cached.data;
  }

  try {
    const item = localStorage.getItem(CACHE_PREFIX + key);
    if (!item) return null;
    const parsed = JSON.parse(item);
    return parsed.data;
  } catch (e) {
    console.warn('Stale cache read error', e);
    return null;
  }
}

async function fetchMetadata() {
  const cached = await getFromStorage('metadata');
  if (cached) return cached;

  try {
    const root = window.ROOT_PATH || '';
    // Prefer static file first as this is a static site by default
    // API fallback removed or secondary as per Zero Budget model
    let url = `${root}metadata.json${getCacheBust()}`;

    try {
      const response = await fetchWithRetry(url, 3, 1000);
      const data = await response.json();
      await saveToStorage('metadata', data, 120000);
      return data;
    } catch (staticError) {
      // Try API if static fails (e.g. running locally with backend server)
      url = `${root}api/stats${getCacheBust()}`;
      const response = await fetchWithRetry(url, 3, 1000);
      const data = await response.json();
      await saveToStorage('metadata', data, 120000); // Default expiry if fallback
      return data;
    }
  } catch (error) {
    console.error('❌ Failed to fetch metadata:', error);
    // Return stale cache if available as last resort
    const stale = await getStaleFromStorage('metadata');
    if (stale) return stale;
    throw error;
  }
}

function enrichProxyList(data, { fallback = false } = {}) {
  return data.map(proxy => {
    const latencyValue = proxy.latency ?? proxy.latency_ms ?? null;
    const isWorking = proxy.is_working !== false;
    return {
      ...proxy,
      source: fallback ? 'fallback' : 'primary',
      location: {
        city: proxy.city || 'Unknown',
        country: proxy.country_code || 'XX',
        flag: getCountryFlag(proxy.country_code)
      },
      latency: latencyValue,
      is_working: isWorking,
      protocolColor: getProtocolColor(proxy.protocol),
      statusIcon: getStatusIcon(isWorking)
    };
  });
}

async function fetchFallbackSnapshot() {
  const root = window.ROOT_PATH || '';
  const fallbackUrl = `${root}proxies.json${getCacheBust()}`;
  console.warn('⚠️ Falling back to tested proxy snapshot');
  const response = await fetchWithRetry(fallbackUrl, 2, 1500);
  const payload = await response.json();
  if (!Array.isArray(payload)) throw new Error('Invalid fallback proxy payload: expected array');
  return enrichProxyList(payload, { fallback: true });
}

async function fetchProxies() {
  const cached = await getFromStorage('proxies');
  if (cached) return cached;

  let enrichedProxies;
  try {
    const root = window.ROOT_PATH || '';
    // Prefer static file first (proxies.json)
    const url = `${root}proxies.json${getCacheBust()}`;
    const response = await fetchWithRetry(url, 2, 500);
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error('Invalid proxy data format: expected array');
    enrichedProxies = enrichProxyList(data);
    if (enrichedProxies.length === 0) {
      console.warn('⚠️ Primary proxy list is empty, attempting fallback.');
      enrichedProxies = await fetchFallbackSnapshot();
    }
  } catch (primaryError) {
    // Try API fallback
    try {
        const root = window.ROOT_PATH || '';
        const url = `${root}api/proxies${getCacheBust()}`;
        const response = await fetchWithRetry(url, 2, 500);
        const data = await response.json();
        if (!Array.isArray(data)) throw new Error('Invalid proxy data format');
        enrichedProxies = enrichProxyList(data);
    } catch(apiError) {
        console.error(`❌ Failed to fetch primary proxies.json: ${primaryError.message}. Attempting fallback.`);
        try {
          enrichedProxies = await fetchFallbackSnapshot();
        } catch (fallbackError) {
          console.error('❌ Fallback snapshot also failed:', fallbackError);
          // Return stale cache if available
          const stale = await getStaleFromStorage('proxies');
          if (stale) return stale;
          throw primaryError;
        }
    }
  }
  await saveToStorage('proxies', enrichedProxies, 600000);
  return enrichedProxies;
}

async function fetchStatistics() {
  // [UNIFIED] Statistics now fetches from metadata.json - single source of truth
  // All analytics data including globe points are now in metadata.json
  const cached = await getFromStorage('statistics');
  if (cached) return cached;

  try {
    const root = window.ROOT_PATH || '';
    const url = `${root}metadata.json${getCacheBust()}`;

    const response = await fetchWithRetry(url, 3, 1000);
    const data = await response.json();
    await saveToStorage('statistics', data, 300000);
    return data;
  } catch (error) {
    console.error('❌ Failed to fetch statistics:', error);
    const stale = await getStaleFromStorage('statistics');
    if (stale) return stale;
    throw error;
  }
}
