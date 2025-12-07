/**
 * Utils Facade
 * Connects the split utility modules to the global window.api
 */

// Expose global API
window.api = {
  fetchProxies: typeof fetchProxies !== 'undefined' ? fetchProxies : null,
  fetchMetadata: typeof fetchMetadata !== 'undefined' ? fetchMetadata : null,
  fetchStatistics: typeof fetchStatistics !== 'undefined' ? fetchStatistics : null,
  clearCache: typeof clearCache !== 'undefined' ? clearCache : null,
  initMobileNav: typeof initMobileNav !== 'undefined' ? initMobileNav : null,
  initTheme: typeof initTheme !== 'undefined' ? initTheme : null
};

// Export for testing if in Node.js environment
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    // getCountryFlag, etc. would be undefined here if not loaded,
    // but this file is just a facade in this context.
  };
}

// Ensure window.api is properly exported for all page scripts
if (typeof window !== 'undefined') {
    // Re-export from network.js if functions exist
    window.api = window.api || {};

    // Bind functions if they exist in current scope or from imports
    // Note: In vanilla JS without modules, we rely on other scripts loading these functions into global scope
    // We bind them here just in case they are available now, or we might need a loader to bind them later.

    // A more robust way for vanilla JS is to let the other files attach themselves to window.api or window directly.
    // But per the request, we ensure window.api exists.

    if (typeof fetchProxies === 'function') window.api.fetchProxies = fetchProxies;
    if (typeof fetchMetadata === 'function') window.api.fetchMetadata = fetchMetadata;
    if (typeof fetchStatistics === 'function') window.api.fetchStatistics = fetchStatistics;
    if (typeof clearCache === 'function') window.api.clearCache = clearCache;
    if (typeof initMobileNav === 'function') window.api.initMobileNav = initMobileNav;
    if (typeof initTheme === 'function') window.api.initTheme = initTheme;

    console.log('✅ window.api initialized:', Object.keys(window.api));
}

console.log('✅ Enhanced utils.js (Facade) loaded');
