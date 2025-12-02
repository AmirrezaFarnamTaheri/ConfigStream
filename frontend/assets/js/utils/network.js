/**
 * Network and Caching utilities
 */

// Use centralized cache configuration from cache-config.js if available
const CACHE_CONFIG = window.ConfigStreamCache?.CACHE_CONFIG || {
  metadataExpiry: 2 * 60 * 1000,
  proxiesExpiry: 10 * 60 * 1000,
  statsExpiry: 5 * 60 * 1000,
};

const cache = {
  metadata: { data: null, expiry: 0 },
  proxies: { data: null, expiry: 0 },
  statistics: { data: null, expiry: 0 },
};

function getCacheBust() {
  return `?cb=${Date.now()}`;
}

function isCacheValid(key) {
  if (!cache[key] || !cache[key].data) return false;
  return Date.now() < cache[key].expiry;
}

function clearCache() {
  Object.keys(cache).forEach(key => {
    cache[key] = { data: null, expiry: 0 };
  });
  console.log('🗑️ Cache cleared');
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

async function fetchMetadata() {
  if (isCacheValid('metadata')) {
    console.log('📦 Using cached metadata');
    return cache.metadata.data;
  }
  try {
    const url = `/api/stats${getCacheBust()}`;
    const response = await fetchWithRetry(url, 3, 1000);
    const data = await response.json();
    cache.metadata = { data, expiry: Date.now() + CACHE_CONFIG.metadataExpiry };
    return data;
  } catch (error) {
    console.error('❌ Failed to fetch metadata:', error);
    if (cache.metadata.data) return cache.metadata.data;
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
  const fallbackUrl = `proxies.json${getCacheBust()}`;
  console.warn('⚠️ Falling back to tested proxy snapshot');
  const response = await fetchWithRetry(fallbackUrl, 2, 1500);
  const payload = await response.json();
  if (!Array.isArray(payload)) throw new Error('Invalid fallback proxy payload: expected array');
  return enrichProxyList(payload, { fallback: true });
}

async function fetchProxies() {
  if (isCacheValid('proxies')) {
    console.log('📦 Using cached proxies');
    return cache.proxies.data;
  }
  let enrichedProxies;
  try {
    const url = `/api/proxies${getCacheBust()}`;
    const response = await fetchWithRetry(url, 2, 500);
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error('Invalid proxy data format: expected array');
    enrichedProxies = enrichProxyList(data);
    if (enrichedProxies.length === 0) {
      console.warn('⚠️ Primary proxy list is empty, attempting fallback.');
      enrichedProxies = await fetchFallbackSnapshot();
    }
  } catch (primaryError) {
    console.error(`❌ Failed to fetch primary proxies.json: ${primaryError.message}. Attempting fallback.`);
    try {
      enrichedProxies = await fetchFallbackSnapshot();
    } catch (fallbackError) {
      console.error('❌ Fallback snapshot also failed:', fallbackError);
      if (cache.proxies.data) return cache.proxies.data;
      throw primaryError;
    }
  }
  cache.proxies = { data: enrichedProxies, expiry: Date.now() + CACHE_CONFIG.proxiesExpiry };
  console.log(`✅ Loaded ${enrichedProxies.length} proxies`);
  return enrichedProxies;
}

async function fetchStatistics() {
  if (isCacheValid('statistics')) {
    console.log('📦 Using cached statistics');
    return cache.statistics.data;
  }
  try {
    let url = `/api/stats${getCacheBust()}`;
    try {
        const response = await fetchWithRetry(url, 3, 1000);
        const data = await response.json();
        cache.statistics = { data, expiry: Date.now() + CACHE_CONFIG.statsExpiry };
        return data;
    } catch (apiError) {
        console.warn('API fetch failed, trying static fallback for stats:', apiError);
        url = `metadata.json${getCacheBust()}`;
        const response = await fetchWithRetry(url, 3, 1000);
        const data = await response.json();
        cache.statistics = { data, expiry: Date.now() + CACHE_CONFIG.statsExpiry };
        return data;
    }
  } catch (error) {
    console.error('❌ Failed to fetch statistics:', error);
    if (cache.statistics.data) return cache.statistics.data;
    throw error;
  }
}
