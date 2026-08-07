/**
 * Network and Caching utilities
 * Integrates with CacheManager if available, otherwise falls back to LocalStorage.
 * Public artifact reads are fail-closed through ConfigStreamArtifactState.
 */

const CACHE_PREFIX = 'configstream_cache_';

function getCacheBust() {
  return `?cb=${Date.now()}`;
}

function isLocalArtifactContext() {
  const hostname = String(window.location?.hostname || '').replace(/^\[|\]$/g, '').toLowerCase();
  if (!hostname || hostname === 'localhost' || hostname.endsWith('.localhost') || hostname === '::1') {
    return true;
  }
  const parts = hostname.split('.').map(Number);
  return parts.length === 4 && parts.every(Number.isInteger) && parts[0] === 127;
}

async function requireVerifiedArtifact() {
  const artifact = window.ConfigStreamArtifactState;
  if (!artifact) {
    if (isLocalArtifactContext()) return null;
    throw new Error('Artifact verifier unavailable in public context');
  }

  const state = await (artifact.ready || artifact.verify());
  if (!state || state.canDistribute !== true) {
    if (isLocalArtifactContext()) return null;
    throw new Error(state?.reason || 'Artifact verification failed');
  }
  return artifact;
}

async function fetchVerifiedArtifactJson(path) {
  const artifact = await requireVerifiedArtifact();
  if (!artifact) return null;
  return artifact.fetchVerifiedJson(path);
}

async function getFromStorage(key) {
  if (window.cacheManager && window.cacheManager.cacheAvailable) {
      const url = getUrlForKey(key);
      const cached = await window.cacheManager.getCachedData(url);
      if (!cached) return null;

      const expiryMs = cached.expiry ?? window.cacheManager.getExpiryForUrl(url);
      if (window.cacheManager.isExpired(cached, expiryMs)) {
        return null;
      }

      return cached.data;
  }

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
  if (window.cacheManager && window.cacheManager.cacheAvailable) {
      const url = getUrlForKey(key);
      await window.cacheManager.cacheData(url, data);
      return;
  }
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
  const verified = await fetchVerifiedArtifactJson('metadata.json');
  if (verified !== null) return verified;

  const cached = await getFromStorage('metadata');
  if (cached) return cached;

  try {
    const root = window.ROOT_PATH || '';
    let url = `${root}metadata.json${getCacheBust()}`;

    try {
      const response = await fetchWithRetry(url, 3, 1000);
      const data = await response.json();
      await saveToStorage('metadata', data, 120000);
      return data;
    } catch (staticError) {
      url = `${root}api/stats${getCacheBust()}`;
      const response = await fetchWithRetry(url, 3, 1000);
      const data = await response.json();
      await saveToStorage('metadata', data, 120000);
      return data;
    }
  } catch (error) {
    console.error('❌ Failed to fetch metadata:', error);
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
  const verified = await fetchVerifiedArtifactJson('proxies.json');
  if (verified !== null) {
    if (!Array.isArray(verified)) throw new Error('Invalid verified proxy payload: expected array');
    return enrichProxyList(verified, { fallback: true });
  }

  const root = window.ROOT_PATH || '';
  const fallbackUrl = `${root}proxies.json${getCacheBust()}`;
  console.warn('⚠️ Falling back to tested proxy snapshot');
  const response = await fetchWithRetry(fallbackUrl, 2, 1500);
  const payload = await response.json();
  if (!Array.isArray(payload)) throw new Error('Invalid fallback proxy payload: expected array');
  return enrichProxyList(payload, { fallback: true });
}

async function fetchProxies() {
  const verified = await fetchVerifiedArtifactJson('proxies.json');
  if (verified !== null) {
    if (!Array.isArray(verified)) throw new Error('Invalid verified proxy payload: expected array');
    return enrichProxyList(verified);
  }

  const cached = await getFromStorage('proxies');
  if (cached) return cached;

  let enrichedProxies;
  try {
    const root = window.ROOT_PATH || '';
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
  const verified = await fetchVerifiedArtifactJson('metadata.json');
  if (verified !== null) return verified;

  const cached = await getFromStorage('statistics');
  if (cached) return cached;

  const root = window.ROOT_PATH || '';
  try {
    let url = `${root}metadata.json${getCacheBust()}`;
    try {
      const response = await fetchWithRetry(url, 3, 1000);
      const data = await response.json();
      await saveToStorage('statistics', data, 300000);
      return data;
    } catch (staticError) {
      url = `${root}api/stats${getCacheBust()}`;
      const response = await fetchWithRetry(url, 3, 1000);
      const data = await response.json();
      await saveToStorage('statistics', data, 300000);
      return data;
    }
  } catch (error) {
    console.error('❌ Failed to fetch statistics:', error);
    const stale = await getStaleFromStorage('statistics');
    if (stale) return stale;
    throw error;
  }
}
