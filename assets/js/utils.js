/**
 * Enhanced utility functions with comprehensive input validation
 * All functions handle invalid input gracefully and log warnings for debugging
 */

// Use centralized cache configuration from cache-config.js
// If cache-config is not loaded, fall back to defaults
const CACHE_CONFIG = window.ConfigStreamCache?.CACHE_CONFIG || {
  metadataExpiry: 2 * 60 * 1000,        // 2 minutes
  proxiesExpiry: 10 * 60 * 1000,        // 10 minutes
  statsExpiry: 5 * 60 * 1000,           // 5 minutes
};

// Memory cache for API responses
const cache = {
  metadata: { data: null, expiry: 0 },
  proxies: { data: null, expiry: 0 },
  statistics: { data: null, expiry: 0 },
};

/**
 * Generate cache-busting query parameter
 * @returns {string} Cache-bust token with timestamp
 */
function getCacheBust() {
  return `?cb=${Date.now()}`;
}

/**
 * Check if cached data is still valid
 * @param {string} key Cache key
 * @returns {boolean} True if cache is valid
 */
function isCacheValid(key) {
  if (!cache[key] || !cache[key].data) return false;
  return Date.now() < cache[key].expiry;
}

/**
 * Fetch with retry logic
 * @param {string} url URL to fetch
 * @param {number} retries Number of retries (default: 3)
 * @param {number} delay Delay between retries in ms (default: 1000)
 * @returns {Promise<Response>}
 */
async function fetchWithRetry(url, retries = 3, delay = 1000) {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Cache-Control': 'no-cache'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return response;
    } catch (error) {
      if (i < retries - 1) {
        console.warn(`Fetch attempt ${i + 1} failed, retrying in ${delay}ms:`, error.message);
        await new Promise(resolve => setTimeout(resolve, delay));
        delay = Math.min(delay * 2, 8000); // Exponential backoff, max 8s
      } else {
        throw error;
      }
    }
  }
}

/**
 * Fetch metadata with caching
 * @returns {Promise<Object>} Metadata object
 */
async function fetchMetadata() {
  if (isCacheValid('metadata')) {
    console.log('📦 Using cached metadata');
    return cache.metadata.data;
  }

  try {
    const url = `output/metadata.json${getCacheBust()}`;
    const response = await fetchWithRetry(url, 3, 1000);
    const data = await response.json();

    cache.metadata = {
      data,
      expiry: Date.now() + CACHE_CONFIG.metadataExpiry
    };

    return data;
  } catch (error) {
    console.error('❌ Failed to fetch metadata:', error);
    if (cache.metadata.data) {
      console.log('📦 Using stale metadata from cache');
      return cache.metadata.data;
    }
    throw error;
  }
}

/**
 * Fetch all proxies with caching and pagination support
 * @returns {Promise<Array>} Array of proxy objects
 */
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
  const fallbackUrl = `output/full/all.json${getCacheBust()}`;
  console.warn('⚠️ Falling back to tested proxy snapshot');
  const response = await fetchWithRetry(fallbackUrl, 2, 1500);
  const payload = await response.json();

  if (!Array.isArray(payload)) {
    throw new Error('Invalid fallback proxy payload: expected array');
  }

  return enrichProxyList(payload, { fallback: true });
}

async function fetchProxies() {
  if (isCacheValid('proxies')) {
    console.log('📦 Using cached proxies');
    return cache.proxies.data;
  }

  let enrichedProxies;

  try {
    // First, try to fetch the primary, smaller file
    const url = `output/proxies.json${getCacheBust()}`;
    const response = await fetchWithRetry(url, 2, 500); // Shorter timeout for the primary
    const data = await response.json();

    if (!Array.isArray(data)) {
      throw new Error('Invalid proxy data format: expected array');
    }

    enrichedProxies = enrichProxyList(data);

    // If the primary file is empty, immediately try the fallback
    if (enrichedProxies.length === 0) {
      console.warn('⚠️ Primary proxy list is empty, attempting fallback.');
      enrichedProxies = await fetchFallbackSnapshot();
    }
  } catch (primaryError) {
    console.error(`❌ Failed to fetch primary proxies.json: ${primaryError.message}. Attempting fallback.`);
    try {
      // If the primary fetch fails for any reason (e.g., 404), try the fallback
      enrichedProxies = await fetchFallbackSnapshot();
    } catch (fallbackError) {
      console.error('❌ Fallback snapshot also failed:', fallbackError);
      // If stale data is available, use it as a last resort
      if (cache.proxies.data) {
        console.log('📦 Using stale proxies from cache as last resort.');
        return cache.proxies.data;
      }
      // If there's no cache, re-throw the original error to be caught by the UI
      throw primaryError;
    }
  }

  // Cache the successfully fetched (or fallback) data
  cache.proxies = {
    data: enrichedProxies,
    expiry: Date.now() + CACHE_CONFIG.proxiesExpiry
  };

  console.log(`✅ Loaded ${enrichedProxies.length} proxies${
    enrichedProxies.length > 0 && enrichedProxies[0].source === 'fallback' ? ' (from fallback)' : ''
  }`);

  return enrichedProxies;
}

/**
 * Fetch statistics with caching
 * @returns {Promise<Object>} Statistics object
 */
async function fetchStatistics() {
  if (isCacheValid('statistics')) {
    console.log('📦 Using cached statistics');
    return cache.statistics.data;
  }

  try {
    const url = `output/statistics.json${getCacheBust()}`;
    const response = await fetchWithRetry(url, 3, 1000);
    const data = await response.json();

    console.log('Fetched statistics data:', data);

    cache.statistics = {
      data,
      expiry: Date.now() + CACHE_CONFIG.statsExpiry
    };

    return data;
  } catch (error) {
    console.error('❌ Failed to fetch statistics:', error);
    if (cache.statistics.data) {
      console.log('📦 Using stale statistics from cache');
      return cache.statistics.data;
    }
    throw error;
  }
}

/**
 * Get color for protocol badge
 * @param {string} protocol Protocol name
 * @returns {string} CSS class or hex color
 */
function getProtocolColor(protocol) {
  const colors = {
    'vmess': '#FF6B6B',
    'vless': '#4ECDC4',
    'shadowsocks': '#45B7D1',
    'trojan': '#96CEB4',
    'hysteria': '#FFEAA7',
    'hysteria2': '#DFE6E9',
    'tuic': '#A29BFE',
    'wireguard': '#74B9FF',
    'naive': '#FD79A8',
    'http': '#FDCB6E',
    'https': '#6C5CE7',
    'socks': '#00B894'
  };
  return colors[protocol?.toLowerCase()] || '#95A5A6';
}
/**
 * Converts country code to flag emoji with full validation
 *
 * @param {string} countryCode - Two-letter ISO country code (e.g., 'US', 'FR')
 * @returns {string} Flag emoji or globe emoji if invalid
 *
 * Examples:
 *   getCountryFlag('US') → '🇺🇸'
 *   getCountryFlag('fr') → '🇫🇷' (case insensitive)
 *   getCountryFlag(null) → '🌍' (handles null)
 *   getCountryFlag('USA') → '🌍' (handles wrong length)
 */
function getCountryFlag(countryCode) {
  // Step 1: Type validation
  if (countryCode === null || countryCode === undefined) {
    console.debug('[getCountryFlag] Null or undefined input');
    return '🌍';
  }

  if (typeof countryCode !== 'string') {
    console.warn(`[getCountryFlag] Expected string, got ${typeof countryCode}`);
    return '🌍';
  }

  // Step 2: Format validation
  const trimmed = countryCode.trim();

  if (trimmed.length === 0) {
    console.debug('[getCountryFlag] Empty string input');
    return '🌍';
  }

  if (trimmed.length !== 2) {
    console.warn(`[getCountryFlag] Expected 2 characters, got ${trimmed.length}: "${trimmed}"`);
    return '🌍';
  }

  // Step 3: Character validation (must be letters only)
  if (!/^[A-Za-z]{2}$/.test(trimmed)) {
    console.warn(`[getCountryFlag] Expected letters only, got: "${trimmed}"`);
    return '🌍';
  }

  // Step 4: Generate flag emoji
  try {
    const upperCode = trimmed.toUpperCase();

    // Convert to regional indicator symbols
    // 'US' becomes 🇺 + 🇸 which displays as 🇺🇸
    const codePoints = upperCode
      .split('')
      .map(char => {
        // Regional Indicator Symbol Letter A starts at 0x1F1E6
        // 'A'.charCodeAt(0) is 65, so we add 0x1F1E6 - 65 = 127397
        return 127397 + char.charCodeAt(0);
      });

    return String.fromCodePoint(...codePoints);
  } catch (error) {
    console.error('[getCountryFlag] Failed to generate flag emoji:', error);
    return '🌍';
  }
}

/**
 * Format timestamp with validation and error handling
 *
 * @param {Date|string|number} timestamp - Date to format
 * @param {string} format - Format string (default: 'MM/DD/YYYY HH:mm:ss')
 * @returns {string} Formatted date or 'N/A' if invalid
 *
 * Supported format tokens:
 *   YYYY - 4-digit year
 *   MM   - 2-digit month
 *   DD   - 2-digit day
 *   HH   - 2-digit hours (24-hour)
 *   mm   - 2-digit minutes
 *   ss   - 2-digit seconds
 */
function formatTimestamp(timestamp, format = 'MM/DD/YYYY HH:mm:ss') {
  // Step 1: Null check
  if (timestamp === null || timestamp === undefined) {
    console.debug('[formatTimestamp] Null or undefined input');
    return 'N/A';
  }

  // Step 2: Convert to Date object
  let dateObj;

  try {
    if (timestamp instanceof Date) {
      dateObj = timestamp;
    } else if (typeof timestamp === 'number') {
      // Unix timestamp (milliseconds)
      dateObj = new Date(timestamp);
    } else if (typeof timestamp === 'string') {
      // ISO string or other parseable format
      dateObj = new Date(timestamp);
    } else {
      console.warn(`[formatTimestamp] Unsupported type: ${typeof timestamp}`);
      return 'N/A';
    }
  } catch (error) {
    console.error('[formatTimestamp] Error creating Date object:', error);
    return 'N/A';
  }

  // Step 3: Validate date is valid
  if (isNaN(dateObj.getTime())) {
    console.warn(`[formatTimestamp] Invalid date: ${timestamp}`);
    return 'Invalid Date';
  }

  // Step 4: Check for unrealistic dates
  const year = dateObj.getFullYear();
  if (year < 1970 || year > 2100) {
    console.warn(`[formatTimestamp] Unrealistic year: ${year}`);
    return 'N/A';
  }

  // Step 5: Format the date
  try {
    const parts = {
      YYYY: dateObj.getFullYear().toString(),
      MM: String(dateObj.getMonth() + 1).padStart(2, '0'),
      DD: String(dateObj.getDate()).padStart(2, '0'),
      HH: String(dateObj.getHours()).padStart(2, '0'),
      mm: String(dateObj.getMinutes()).padStart(2, '0'),
      ss: String(dateObj.getSeconds()).padStart(2, '0')
    };

    let result = format;
    for (const [token, value] of Object.entries(parts)) {
      result = result.replace(token, value);
    }

    return result;
  } catch (error) {
    console.error('[formatTimestamp] Error formatting date:', error);
    return 'Format Error';
  }
}

/**
 * Safely update DOM element content with validation
 *
 * @param {string} selector - CSS selector for element
 * @param {string|number|HTMLElement} content - Content to set
 * @param {Object} options - Configuration options
 * @param {string} options.method - 'textContent' or 'innerHTML'
 * @param {boolean} options.clearFirst - Clear existing content first
 * @param {boolean} options.throwError - Throw errors instead of logging
 * @param {boolean} options.trustedHTML - Skip sanitization for trusted internal HTML
 * @returns {boolean} Success indicator
 */
function updateElement(selector, content, options = {}) {
  console.log(`Updating element ${selector} with content:`, content);
  const {
    method = 'textContent',
    clearFirst = false,
    throwError = false,
    trustedHTML = false
  } = options;

  // Step 1: Validate selector
  if (!selector || typeof selector !== 'string') {
    const msg = '[updateElement] Selector must be a non-empty string';
    console.error(msg);
    if (throwError) throw new TypeError(msg);
    return false;
  }

  // Step 2: Validate content
  if (content === null || content === undefined) {
    const msg = '[updateElement] Content cannot be null or undefined';
    console.warn(msg);
    if (throwError) throw new TypeError(msg);
    return false;
  }

  // Step 3: Find element
  let element;
  try {
    element = document.querySelector(selector);
  } catch (error) {
    const msg = `[updateElement] Invalid selector: ${selector}`;
    console.error(msg, error);
    if (throwError) throw error;
    return false;
  }

  if (!element) {
    const msg = `[updateElement] Element not found: ${selector}`;
    console.warn(msg);
    if (throwError) throw new Error(msg);
    return false;
  }

  // Step 4: Clear if requested
  if (clearFirst) {
    element.innerHTML = '';
  }

  // Step 5: Set content based on method
  try {
    if (method === 'innerHTML') {
      // WARNING: innerHTML can execute scripts if content contains malicious HTML
      // Only use trustedHTML for internal, verified content
      if (trustedHTML) {
        element.innerHTML = String(content);
      } else {
        const sanitized = sanitizeHTML(String(content));
        element.innerHTML = sanitized;
      }
    } else if (method === 'textContent') {
      // Safe: textContent automatically escapes HTML
      element.textContent = String(content);
    } else {
      console.error(`[updateElement] Unknown method: ${method}`);
      return false;
    }

    element.classList.remove('loading');
    return true;
  } catch (error) {
    console.error('[updateElement] Error setting content:', error);
    if (throwError) throw error;
    return false;
  }
}

/**
 * Basic HTML sanitization to prevent XSS
 * This is a simple implementation. For production, consider DOMPurify library.
 *
 * @param {string} html - HTML string to sanitize
 * @returns {string} Sanitized HTML
 */
function sanitizeHTML(html) {
  const div = document.createElement('div');
  div.textContent = html;
  return div.innerHTML;
}

/**
 * Parse latency value with validation
 *
 * @param {any} value - Value to parse as latency
 * @returns {number} Latency in milliseconds, or -1 if invalid
 */
function parseLatency(value) {
  // Step 1: Null check
  if (value === null || value === undefined) {
    return -1;
  }

  // Step 2: Convert to number
  const num = Number(value);

  if (isNaN(num)) {
    console.warn(`[parseLatency] Not a number: ${value}`);
    return -1;
  }

  // Step 3: Range validation
  if (num < 0) {
    console.warn(`[parseLatency] Negative latency: ${num}`);
    return -1;
  }

  if (num > 100000) {
    console.warn(`[parseLatency] Unrealistic latency: ${num}ms (>100s)`);
    return -1;
  }

  // Step 4: Round to integer
  return Math.round(num);
}

/**
 * Validate and normalize URL
 *
 * @param {string} url - URL to validate
 * @returns {string|null} Valid URL or null if invalid
 */
function validateURL(url) {
  // Step 1: Type and null check
  if (!url || typeof url !== 'string') {
    return null;
  }

  // Step 2: Try to parse URL
  try {
    const urlObj = new URL(url);

    // Step 3: Only allow safe protocols
    const allowedProtocols = ['http:', 'https:'];
    if (!allowedProtocols.includes(urlObj.protocol)) {
      console.warn(`[validateURL] Unsafe protocol: ${urlObj.protocol}`);
      return null;
    }

    // Step 4: Check for valid hostname
    if (!urlObj.hostname || urlObj.hostname.length === 0) {
      console.warn('[validateURL] Missing hostname');
      return null;
    }

    // Step 5: Return normalized URL
    return urlObj.toString();
  } catch (error) {
    console.warn(`[validateURL] Invalid URL: ${url}`, error.message);
    return null;
  }
}

/**
 * Deep clone object safely
 *
 * @param {any} obj - Object to clone
 * @returns {any} Cloned object or null if not serializable
 */
function deepClone(obj) {
  // Null/undefined pass through
  if (obj === null || obj === undefined) {
    return obj;
  }

  // Primitives pass through
  if (typeof obj !== 'object') {
    return obj;
  }

  // Clone using JSON (simple but effective for plain objects)
  try {
    return JSON.parse(JSON.stringify(obj));
  } catch (error) {
    console.error('[deepClone] Failed to clone object:', error);
    return null;
  }
}

/**
 * Debounce function to limit execution rate
 * Useful for expensive operations like search
 *
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
  let timeout;

  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };

    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function to limit execution rate
 * Different from debounce: executes immediately then blocks subsequent calls
 *
 * @param {Function} func - Function to throttle
 * @param {number} limit - Limit time in milliseconds
 * @returns {Function} Throttled function
 */
function throttle(func, limit) {
  let inThrottle;

  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Get status icon
 * @param {boolean} isWorking Working status
 * @returns {string} Status icon emoji
 */
function getStatusIcon(isWorking) {
  return isWorking ? '✅' : '❌';
}

/**
 * Clear all caches
 */
function clearCache() {
  Object.keys(cache).forEach(key => {
    cache[key] = { data: null, expiry: 0 };
  });
  console.log('🗑️ Cache cleared');
}

/**
 * Export object as JSON file
 * @param {Object} data Data to export
 * @param {string} filename Filename for export
 */
function exportJSON(data, filename = 'export.json') {
  const jsonString = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * Get full URL for a file
 * @param {string} file - File path
 * @returns {string} Full URL
 */
function getFullUrl(file) {
  const base = window.location.origin + window.location.pathname.replace(/\/[^/]*$/, '/');
  return base + file;
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @param {HTMLElement} button - Button element for feedback
 */
async function copyToClipboard(text, button) {
  try {
    await navigator.clipboard.writeText(text);

    // Visual feedback
    const originalHTML = button.innerHTML;
    button.innerHTML = '<i data-feather="check"></i>';
    if (window.inlineIcons) {
      window.inlineIcons.replace();
    }
    button.classList.add('copied');

    setTimeout(() => {
      button.innerHTML = originalHTML;
      if (window.inlineIcons) {
        window.inlineIcons.replace();
      }
      button.classList.remove('copied');
    }, 2000);
  } catch (error) {
    console.error('Failed to copy:', error);
    button.innerHTML = '<i data-feather="x"></i>';
    if (window.inlineIcons) {
      window.inlineIcons.replace();
    }
  }
}

// Expose global API
window.api = {
  fetchProxies,
  fetchMetadata,
  fetchStatistics,
  clearCache
};

// Export for testing if in Node.js environment
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    getCountryFlag,
    formatTimestamp,
    updateElement,
    sanitizeHTML,
    parseLatency,
    validateURL,
    deepClone,
    debounce,
    throttle,
    getFullUrl,
    copyToClipboard
  };
}

console.log('✅ Enhanced utils.js loaded');
