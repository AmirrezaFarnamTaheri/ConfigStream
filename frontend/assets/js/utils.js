/**
 * Utils Facade
 * Connects the split utility modules to the global window.api
 */

// Expose global API
window.api = {
  fetchProxies,
  fetchMetadata,
  fetchStatistics,
  clearCache,
  initMobileNav,
  initTheme
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

console.log('✅ Enhanced utils.js (Facade) loaded');
